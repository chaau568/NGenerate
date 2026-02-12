from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Package, Transaction
from .serializers import TransactionQRSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment(request):
    package_id = request.data.get('package_id')
    user = request.user
    
    try:
        package = Package.objects.get(id=package_id, is_active=True)
        transaction = Transaction.objects.create(
            user=user,
            package=package,
            payment_status='pending'
        )
        
        serializer = TransactionQRSerializer(transaction)
        return Response(serializer.data, status=201)
    
    except Package.DoesNotExist:
        return Response({"error": "Package Not Found"}, status=404)