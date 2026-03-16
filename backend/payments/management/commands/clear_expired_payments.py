from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from payments.models import Transaction


class Command(BaseCommand):
    help = f"Expires transactions that are pending for more than {settings.PAYMENTS_EXPIRE_MINUTES} minutes"

    def handle(self, *args, **kwargs):
        expire_minutes = settings.PAYMENTS_EXPIRE_MINUTES
        threshold = timezone.now() - timedelta(minutes=expire_minutes)

        expired_count = Transaction.objects.filter(
            payment_status="pending", created_at__lt=threshold
        ).update(payment_status="expired")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully expired {expired_count} transactions")
        )
