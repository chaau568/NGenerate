from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from payments.services.payment_service import PaymentService
from payments.models import Package, Transaction
from .serializers import PackageSerializer
from rest_framework import status

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
    packages = Package.objects.all().order_by("-create_at")
    serializer = PackageSerializer(packages, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment(request):
    package_id = request.data.get("package_id")
    package = Package.objects.get(id=package_id, is_active=True)

    tx = PaymentService.create_transaction(request.user, package)
    qr = PaymentService.generate_qr_for_transaction(tx.id)

    return Response({
        "transaction_id": tx.id,
        "ref": tx.payment_ref,
        "qr": qr
    })
    
@api_view(["GET"])
@permission_classes([IsAdminUser])
def pending_transactions(request):
    transactions = Transaction.objects.filter(payment_status='pending').select_related('user', 'package').order_by('-created_at')
    
    return Response({
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
    })

@api_view(["POST"])
@permission_classes([IsAdminUser])
def confirm_payment(request, transaction_id):
    tx = Transaction.objects.get(id=transaction_id)

    if tx.payment_status != "pending":
        return Response(
            {"error": "Already processed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    PaymentService.mark_success(tx.id)

    return Response({"status": "success"},status=status.HTTP_200_OK)