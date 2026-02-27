from celery import shared_task
from django.utils import timezone
from payments.models import Transaction


@shared_task
def expire_transactions():
    now = timezone.now()

    expired_count = Transaction.objects.filter(
        payment_status="success", expire_at__lte=now
    ).update(payment_status="expired")

    return f"{expired_count} transactions expired"
