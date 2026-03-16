from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Package(models.Model):

    name = models.CharField(max_length=255, unique=True)

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    credits = models.PositiveIntegerField()

    recommendation = models.CharField(max_length=100, blank=True, null=True)

    features = models.JSONField(default=list)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.credits} credits)"


class Transaction(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions"
    )

    package = models.ForeignKey(Package, on_delete=models.PROTECT)

    PAYMENT_STATUS_CHOICES = (
        ("pending", "PENDING"),
        ("success", "SUCCESS"),
        ("failed", "FAILED"),
        ("expired", "EXPIRED"),
    )

    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    payment_ref = models.CharField(max_length=255, null=True, blank=True)
    omise_charge_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    amount = models.IntegerField()

    credit_amount = models.PositiveIntegerField()
    
    expire_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(payment_status="pending"),
                name="unique_pending_transaction_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.package.name} ({self.payment_status})"


class CreditLog(models.Model):

    TYPE_CHOICES = (
        ("topup", "Topup"),
        ("analysis_lock", "Analysis Lock"),
        ("analysis_complete", "Analysis Complete"),
        ("generation_lock", "Generation Lock"),
        ("generation_complete", "Generation Complete"),
        ("refund", "Refund"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credit_logs"
    )

    transaction = models.ForeignKey(
        "payments.Transaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="credit_logs",
    )

    session = models.ForeignKey(
        "ngenerate_sessions.Session",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="credit_logs",
    )

    type = models.CharField(max_length=30, choices=TYPE_CHOICES)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} | {self.type} | {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["session"]),
        ]
