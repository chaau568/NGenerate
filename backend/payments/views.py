from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from payments.services.payment_service import PaymentService
from payments.models import Package, Transaction, CreditLog
from .serializers import PackageSerializer
from rest_framework import status

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from django.conf import settings
from rest_framework.exceptions import ValidationError


@extend_schema(
    summary="สร้าง Package ใหม่ (Admin Only)",
    request=PackageSerializer,
    responses={201: PackageSerializer},
    tags=["Payments Admin"],
)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_package(request):
    serializer = PackageSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="รายการ Package ที่เปิดใช้งาน (Public)",
    responses={200: PackageSerializer(many=True)},
    tags=["Payments Public"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def list_packages(request):
    packages = Package.objects.filter(is_active=True).order_by("price")
    serializer = PackageSerializer(packages, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="รายการ Package ทั้งหมดรวมที่ปิดใช้งาน (Admin Only)",
    responses={200: PackageSerializer(many=True)},
    tags=["Payments Admin"],
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def list_all_packages(request):
    packages = Package.objects.all().order_by("-create_at")
    serializer = PackageSerializer(packages, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="สร้างรายการชำระเงินและรับ QR Code",
    description="เมื่อเรียก API นี้ ระบบจะสร้าง Transaction และส่งข้อมูลสำหรับการจ่ายเงิน (PromptPay QR) กลับไป",
    request=inline_serializer(
        name="CreatePaymentRequest", fields={"package_id": serializers.IntegerField()}
    ),
    responses={
        200: inline_serializer(
            name="CreatePaymentResponse",
            fields={
                "transaction_id": serializers.IntegerField(),
                "ref": serializers.CharField(),
                "qr": serializers.CharField(help_text="Base64 ของ QR Code"),
            },
        )
    },
    tags=["Payments User"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment(request):
    package_id = request.data.get("package_id")

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

    qr = PaymentService.generate_qr_for_transaction(tx.id)

    expire_min = getattr(settings, "PAYMENTS_EXPIRE_MINUTES")

    return Response(
        {
            "transaction_id": tx.id,
            "ref": tx.payment_ref,
            "qr": qr,
            "amount": str(tx.amount),
            "package_name": package.name,
            "expire_in_minutes": expire_min,
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="รายการรอชำระเงินทั้งหมด (Admin Only)",
    responses={
        200: inline_serializer(
            name="PendingTransactionsResponse",
            fields={
                "transactions": serializers.ListField(
                    child=inline_serializer(
                        name="PendingTransactionDetail",
                        fields={
                            "id": serializers.IntegerField(),
                            "username": serializers.CharField(),
                            "package": serializers.CharField(),
                            "price": serializers.CharField(),
                            "ref": serializers.CharField(),
                            "created_at": serializers.DateTimeField(),
                        },
                    )
                )
            },
        )
    },
    tags=["Payments Admin"],
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
                    "price": str(tx.package.price),
                    "ref": tx.payment_ref,
                    "created_at": tx.created_at,
                }
                for tx in transactions
            ]
        }
    )


@extend_schema(
    summary="กดยืนยันการชำระเงินด้วยมือ (Admin Only)",
    description="ใช้สำหรับแอดมินตรวจสอบยอดเงินแล้วกดยืนยันเพื่อเพิ่ม Credit ให้ผู้ใช้",
    responses={
        200: inline_serializer(
            name="ConfirmSuccess", fields={"status": serializers.CharField()}
        ),
        400: inline_serializer(
            name="ConfirmError", fields={"error": serializers.CharField()}
        ),
    },
    tags=["Payments Admin"],
)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def confirm_payment(request, transaction_id):
    tx = Transaction.objects.get(id=transaction_id)

    if tx.payment_status != "pending":
        return Response(
            {"error": "Already processed"}, status=status.HTTP_400_BAD_REQUEST
        )

    PaymentService.mark_success(tx.id)

    return Response({"status": "success"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_payment(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)

    return Response({"payment_status": tx.payment_status}, status=status.HTTP_200_OK)


@extend_schema(
    summary="ประวัติการชำระเงินของผู้ใช้",
    tags=["Payments User"],
)
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
            "amount": str(tx.amount),
            "status": tx.payment_status,
        }
        for tx in transactions
    ]

    return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    summary="ประวัติการใช้เครดิตของผู้ใช้",
    tags=["Payments User"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_credit_logs(request):
    logs = (
        CreditLog.objects.filter(user=request.user)
        .select_related("session", "transaction")
        .order_by("-created_at")
    )

    def map_status(log_type):
        if "lock" in log_type:
            return "processing"
        if "complete" in log_type or log_type == "refund" or log_type == "topup":
            return "completed"
        return "unknown"

    def map_action(log_type):
        mapping = {
            "analysis_lock": "Analyze",
            "analysis_complete": "Analyze",
            "generation_lock": "Generate",
            "generation_complete": "Generate",
            "topup": "Topup",
            "refund": "Refund",
        }
        return mapping.get(log_type, log_type)

    data = [
        {
            "id": log.id,
            "date_time": log.created_at,
            "activate": map_action(log.type),
            "details": (log.session.name if log.session and log.session.name else "-"),
            "credits": str(log.amount),
            "status": map_status(log.type),
        }
        for log in logs
    ]

    return Response(data, status=status.HTTP_200_OK)
