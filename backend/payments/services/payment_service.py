import uuid

from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from payments.models import Transaction
from users.models import UserCredit
from payments.models import CreditLog
from payments.services.qr_service import QRService


class PaymentService:

    @staticmethod
    def create_transaction(user, package):
        ref = str(uuid.uuid4()).split("-")[0]
        tx = Transaction.objects.create(
            user=user,
            package=package,
            payment_status='pending',
            payment_ref=ref,
            amount=package.price,
            credit_amount=package.credits_limit
        )
        return tx

    @staticmethod
    def generate_qr_for_transaction(transaction_id: int):
        tx = Transaction.objects.get(id=transaction_id)

        if tx.payment_status != 'pending':
            raise ValueError("QR can only be generated for pending transactions")

        return QRService.generate_promptpay_qr(tx.package.price, tx.payment_ref)

    @staticmethod
    @transaction.atomic
    def mark_success(transaction_id: int):

        tx = Transaction.objects.select_for_update().get(id=transaction_id)

        if tx.payment_status != 'pending':
            raise ValueError("Transaction already processed")

        tx.payment_status = 'success'
        tx.start_at = timezone.now()
        tx.expire_at = tx.start_at + timedelta(days=tx.package.duration_days)
        tx.save(update_fields=[
            "payment_status",
            "start_at",
            "expire_at",
            "updated_at"
        ])

        wallet, _ = UserCredit.objects.select_for_update().get_or_create(
            user=tx.user
        )

        wallet.add_credit(tx.package.credits_limit)

        CreditLog.objects.create(
            user=tx.user,
            transaction=tx,
            type='topup',
            amount=tx.package.credits_limit
        )

        return tx