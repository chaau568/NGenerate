from rest_framework import serializers
from .models import Transaction

class TransactionQRSerializer(serializers.ModelSerializer):
    qr_code_base64 = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 
            'package',
            'payment_status',
            'credit_remaining', 
            'qr_code_base64',
        ]
        
    def get_qr_code_base64(self, obj):
        return obj.generate_qr_code()