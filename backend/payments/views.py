import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from payments.services.payment_service import PaymentService
from payments.models import Package, Transaction, CreditLog
from .serializers import PackageSerializer
from rest_framework.exceptions import ValidationError

from payments.services.stripe_service import StripeService

logger = logging.getLogger(__name__)


# ============================================================
# ✅ WEBHOOK — รับแจ้งจาก Stripe เมื่อชำระเงินสำเร็จ
# ============================================================


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = StripeService.construct_event(payload, sig_header)
    except Exception:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        session_id = session["id"]

        try:
            PaymentService.mark_success_by_session(session_id)
        except Exception as e:
            return HttpResponse(str(e), status=400)

    return HttpResponse(status=200)


# ============================================================
# Views
# ============================================================


@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_package(request):
    serializer = PackageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_packages(request):
    packages = Package.objects.filter(is_active=True).order_by("price")
    serializer = PackageSerializer(packages, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def list_all_packages(request):
    packages = Package.objects.all().order_by("-created_at")
    serializer = PackageSerializer(packages, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment(request):
    package_id = request.data.get("package_id")

    if not package_id:
        return Response(
            {"detail": "package_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        package = Package.objects.get(id=package_id, is_active=True)
    except Package.DoesNotExist:
        return Response({"detail": "Package not found"}, status=404)

    try:
        key = request.headers.get("Idempotency-Key")

        if key:
            existing = Transaction.objects.filter(idempotency_key=key).first()
            if existing:
                return Response(
                    {
                        "transaction_id": existing.id,
                        "ref": existing.payment_ref,
                        "amount": existing.amount,
                        "package_name": existing.package.name,
                        "expire_at": existing.expire_at,
                        "expire_in_minutes": 15,
                    },
                    status=200,
                )

        tx = PaymentService.create_transaction(request.user, package)

        if key:
            tx.idempotency_key = key
            tx.save(update_fields=["idempotency_key"])
    except ValidationError as e:
        return Response(
            {"detail": e.detail[0] if isinstance(e.detail, list) else e.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    checkout = PaymentService.create_checkout(tx.id)

    expire_min = getattr(settings, "PAYMENTS_EXPIRE_MINUTES", 15)

    return Response(
        {
            "transaction_id": tx.id,
            "ref": tx.payment_ref,
            "checkout_url": checkout["checkout_url"],
            "session_id": checkout["session_id"],
            "amount": tx.amount,
            "package_name": package.name,
            "expire_at": tx.expire_at,
            "expire_in_minutes": expire_min,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)

    if not tx.stripe_session_id:
        checkout = PaymentService.create_checkout(tx.id)
    else:
        checkout = PaymentService.create_checkout(tx.id)

    return Response(
        {
            "transaction_id": tx.id,
            "ref": tx.payment_ref,
            "checkout_url": checkout.get("checkout_url"),
            "session_id": checkout.get("session_id"),
            "amount": tx.amount,
            "package_name": tx.package.name,
            "expire_at": tx.expire_at,
            "expire_in_minutes": 15,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_package(request, package_id):
    """Admin: แก้ไข package (partial update)"""
    package = get_object_or_404(Package, id=package_id)
    serializer = PackageSerializer(package, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_package(request, package_id):
    """Admin: ลบ package"""
    package = get_object_or_404(Package, id=package_id)
    package.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def pending_transactions(request):
    transactions = (
        Transaction.objects.filter(payment_status="pending")
        .select_related("user", "package")
        .order_by("-created_at")
    )
    return Response(
        {
            "transactions": [
                {
                    "id": tx.id,
                    "username": tx.user.username,
                    "package": tx.package.name,
                    "price": tx.package.price,
                    "ref": tx.payment_ref,
                    "stripe_session_id": tx.stripe_session_id,
                    "created_at": tx.created_at,
                }
                for tx in transactions
            ]
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def confirm_payment(request, transaction_id):
    """Admin manual confirm ยังใช้ได้อยู่ (fallback)"""
    tx = get_object_or_404(Transaction, id=transaction_id)

    if tx.payment_status != "pending":
        return Response(
            {"error": "Already processed"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        PaymentService.mark_success(tx.id)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"status": "success"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_session(request):
    session_id = request.data.get("session_id")

    if not session_id:
        return Response({"error": "missing session_id"}, status=400)

    try:
        tx = Transaction.objects.get(stripe_session_id=session_id)
    except Transaction.DoesNotExist:
        return Response({"error": "not found"}, status=404)

    return Response({"status": tx.payment_status})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_payment(request, transaction_id):
    """Frontend polling endpoint — เช็คสถานะ transaction"""
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    return Response({"payment_status": tx.payment_status}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_payments(request):
    transactions = (
        Transaction.objects.filter(user=request.user)
        .select_related("package")
        .order_by("-created_at")
    )
    data = [
        {
            "id": tx.id,
            "date_time": tx.created_at,
            "package": tx.package.name,
            "amount": tx.amount,
            "status": tx.payment_status,
        }
        for tx in transactions
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_credit_logs(request):
    logs = (
        CreditLog.objects.filter(user=request.user)
        .select_related("session", "transaction", "transaction__package")
        .order_by("-created_at")
    )

    ACTION_MAP = {
        "analysis_lock": "Analyze",
        "analysis_complete": "Analyze",
        "generation_lock": "Generate",
        "generation_complete": "Generate",
        "topup": "Topup",
        "refund": "Refund",
    }

    ANALYSIS_SESSION_STATUS_MAP = {
        "analyzing": "processing",
        "analyzed": "completed",
        "failed": "failed",
        "draft": "processing",
    }

    def get_generation_status(session):
        if session is None:
            return "completed"
        latest_run = session.generation_runs.order_by("-version").first()
        if latest_run is None:
            return "processing"
        return {
            "pending": "processing",
            "generating": "processing",
            "generated": "completed",
            "failed": "failed",
        }.get(latest_run.status, "processing")

    def map_status(log):
        t = log.type
        if t in ("analysis_complete", "generation_complete"):
            return "completed"
        if t == "analysis_lock":
            session = log.session
            if session is None:
                return "completed"
            return ANALYSIS_SESSION_STATUS_MAP.get(session.status, "processing")
        if t == "generation_lock":
            return get_generation_status(log.session)
        if t in ("refund", "topup"):
            return "completed"
        return "unknown"

    def map_details(log):
        t = log.type
        if t == "topup":
            if log.transaction and log.transaction.package:
                return log.transaction.package.name
            return "-"
        session_name = (
            (log.session.name if log.session else None) or log.session_name or "-"
        )
        if t == "refund":
            return f"{session_name} (refunded)"
        return session_name

    COMPLETE_TYPES = {"analysis_complete", "generation_complete"}

    complete_set: set[tuple] = set()
    for log in logs:
        if log.type in COMPLETE_TYPES:
            session_id = log.session_id
            complete_set.add((session_id, log.type))

    result = []
    for log in logs:
        if log.type in COMPLETE_TYPES:
            continue

        result.append(
            {
                "id": log.id,
                "date_time": log.created_at,
                "activate": ACTION_MAP.get(log.type, log.type),
                "details": map_details(log),
                "credits": log.amount,
                "status": map_status(log),
            }
        )

    return Response(result, status=status.HTTP_200_OK)
