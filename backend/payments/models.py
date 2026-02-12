from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta

import qrcode
import base64
from io import BytesIO
import promptpay

from django.conf import settings

class Package(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0)],
    )
    credits_limit = models.IntegerField(
        default=30,
        validators=[MinValueValidator(30)],
    )
    duration_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)], 
    )
    is_active = models.BooleanField(default=True) 
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    credit_remaining = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'PENDING'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )
    
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending'
    )
    payment_ref = models.CharField(max_length=255, null=True, blank=True)
    
    start_at = models.DateTimeField(null=True, blank=True)
    expire_at = models.DateTimeField(null=True, blank=True)
    
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.package.name} ({self.payment_status})"
    
    def save(self, *args, **kwargs):
        if not self.pk and self.package:
            self.credit_remaining = self.package.credits_limit
            
            if not self.start_at:
                self.start_at = timezone.now()
                
            if not self.expire_at:
                self.expire_at = self.start_at + timedelta(days=self.package.duration_days)
                
        super().save(*args, **kwargs)
        
    def generate_qr_code(self):
        promptpay_id = getattr(settings, 'PROMPTPAY_ID')
        amount = self.package.price
        
        pp = promptpay.PromptPay()
        payload = pp.generate_payload(promptpay_id, amount)
        
        img = qrcode.make(payload)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"

class CreditLog(models.Model):
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE,
        related_name='credit_logs'
    )
    
    TYPE_CHOICES = (
        ('analyze', 'Analyze'),
        ('generate_demo', 'Generate Demo'),
        ('generate_complete', 'Generate Complete'),
    )
    
    usage_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    credit_spend = models.FloatField(
        validators=[MinValueValidator(0.0)],
    )
    create_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction.user.username} used {self.credit_spend} for {self.usage_type}"