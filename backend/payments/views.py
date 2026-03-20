import hashlib
import hmac
import json
import logging
import base64

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

logger = logging.getLogger(__name__)


# ============================================================
# ✅ WEBHOOK — รับแจ้งจาก Omise เมื่อชำระเงินสำเร็จ
# ============================================================


@csrf_exempt  # ต้องปิด CSRF เพราะ Omise ไม่มี CSRF token
@require_POST
def omise_webhook(request):
    # ── Step 1: ดึง signature จาก header ──────────────────────
    raw_body = request.body
    signature = request.META.get("HTTP_OMISE_SIGNATURE", "")
    timestamp = request.META.get("HTTP_OMISE_SIGNATURE_TIMESTAMP", "")

    if not signature:
        logger.warning("Omise webhook: missing signature header")
        return HttpResponse("Missing signature", status=400)

    # ── Step 2: verify HMAC signature ─────────────────────────
    webhook_secret = getattr(settings, "OMISE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("OMISE_WEBHOOK_SECRET not configured")
        return HttpResponse("Server misconfigured", status=500)

    webhook_secret_bytes = base64.b64decode(webhook_secret)

    message = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")

    expected_signature = hmac.new(
        key=webhook_secret_bytes,
        msg=message,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Omise webhook: invalid signature")
        return HttpResponse("Invalid signature", status=400)

    # ── Step 3: parse body ────────────────────────────────────
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    event_key = payload.get("key", "")
    data = payload.get("data", {})

    logger.info(f"Omise webhook received: event={event_key}, charge={data.get('id')}")

    # ── Step 4: handle events ──────────────────────────────────
    if event_key == "charge.complete":
        return _handle_charge_complete(data)

    # Event อื่นๆ ที่เราไม่ได้ handle → คืน 200 เพื่อบอก Omise ว่ารับแล้ว
    # (ถ้าคืน non-2xx Omise จะ retry ซึ่งไม่ต้องการ)
    return HttpResponse("OK", status=200)


def _handle_charge_complete(charge_data: dict) -> HttpResponse:
    """
    Handle event charge.complete
    Omise จะส่ง event นี้เมื่อการชำระเงินสำเร็จ

    charge_data ตัวอย่าง:
    {
        "id": "chrg_test_5ozmfzwkqzv1p21ked3",
        "object": "charge",
        "status": "successful",
        "amount": 29900,          ← satang
        "currency": "thb",
        "metadata": {"payment_ref": "abc123def456"},
        ...
    }
    """
    charge_id = charge_data.get("id")
    charge_status = charge_data.get("status")

    if not charge_id:
        logger.error("charge.complete: missing charge id")
        return HttpResponse("Missing charge id", status=400)

    # ตรวจว่า status เป็น successful จริงๆ
    # (Omise อาจส่ง charge.complete มาแม้ status เป็น failed ด้วย)
    if charge_status != "successful":
        logger.info(
            f"charge.complete: charge {charge_id} status={charge_status}, skipping"
        )
        return HttpResponse("OK", status=200)

    try:
        PaymentService.mark_success_by_charge_id(charge_id)
        logger.info(f"Payment success: charge_id={charge_id}")
    except ValueError as e:
        error_msg = str(e)
        # "Transaction already processed" → idempotent, คืน 200 ได้เลย
        # เพราะ Omise อาจส่ง webhook ซ้ำ เราไม่อยาก retry อีก
        if "already processed" in error_msg:
            logger.info(f"Duplicate webhook for charge {charge_id}, ignoring")
            return HttpResponse("OK", status=200)
        logger.error(f"mark_success_by_charge_id failed: {e}")
        return HttpResponse(str(e), status=400)
    except Exception as e:
        logger.exception(f"Unexpected error processing webhook: {e}")
        # คืน 500 เพื่อให้ Omise retry (ในกรณี DB error ชั่วคราว)
        return HttpResponse("Internal error", status=500)

    return HttpResponse("OK", status=200)


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
        tx = PaymentService.create_transaction(request.user, package)
    except ValidationError as e:
        return Response(
            {"detail": e.detail[0] if isinstance(e.detail, list) else e.detail},
            status=400,
        )

    qr_data = PaymentService.generate_qr_for_transaction(tx.id)

    expire_min = getattr(settings, "PAYMENTS_EXPIRE_MINUTES", 15)

    return Response(
        {
            "transaction_id": tx.id,
            "ref": tx.payment_ref,
            "qr": qr_data["qr"],
            "charge_id": qr_data["charge_id"],
            "amount": tx.amount,
            "package_name": package.name,
            "expire_at": tx.expire_at,
            "expire_in_minutes": expire_min,
        },
        status=status.HTTP_201_CREATED,
    )


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
                    "omise_charge_id": tx.omise_charge_id,
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

    SESSION_STATUS_MAP = {
        "analyzing": "processing",
        "analyzed": "completed",
        "generating": "processing",
        "generated": "completed",
        "failed": "failed",
        "draft": "processing",
    }

    def map_status(log):
        t = log.type

        if t in ("analysis_complete", "generation_complete"):
            return "completed"

        if t in ("analysis_lock", "generation_lock"):
            session = log.session
            if session is None:
                return "completed"
            return SESSION_STATUS_MAP.get(session.status, "processing")

        if t == "refund":
            return "completed"

        if t == "topup":
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

    data = [
        {
            "id": log.id,
            "date_time": log.created_at,
            "activate": ACTION_MAP.get(log.type, log.type),
            "details": map_details(log),
            "credits": log.amount,
            "status": map_status(log),
        }
        for log in logs
    ]
    return Response(data, status=status.HTTP_200_OK)
