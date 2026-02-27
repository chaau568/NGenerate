from django.db import models
from django.core.validators import MinValueValidator
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
    
    recommendation = models.CharField(max_length=100, blank=True, null=True)
    features = models.JSONField(default=list, help_text="เก็บรายการสิทธิประโยชน์เป็น list ของ string")
    
    is_active = models.BooleanField(default=True) 
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"package: {self.name}"

class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
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
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    credit_amount = models.PositiveIntegerField()
    start_at = models.DateTimeField(null=True, blank=True)
    expire_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(payment_status='pending'),
                name='unique_pending_transaction_per_user'
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(payment_status='success'),
                name='unique_active_success_transaction_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.package.name} ({self.payment_status})"

class CreditLog(models.Model):
    
    TYPE_CHOICES = (
        ('topup', 'Topup'),
        ('analysis_lock', 'Analysis Lock'),
        ('analysis_complete', 'Analysis Complete'),
        ('generation_lock', 'Generation Lock'),
        ('generation_complete', 'Generation Complete'),
        ('refund', 'Refund'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_logs'
    )

    transaction = models.ForeignKey(
        'payments.Transaction',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='credit_logs'
    )

    session = models.ForeignKey(
        'ngenerate_sessions.Session',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='credit_logs'
    )

    type = models.CharField(max_length=30, choices=TYPE_CHOICES)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} | {self.type} | {self.amount}"
