import uuid
import stripe
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from payments.models import Transaction, Package, CreditLog
from users.models import UserCredit
from payments.services.stripe_service import StripeService


class PaymentService:

    @staticmethod
    @transaction.atomic
    def create_transaction(user, package: Package):
        """
        สร้าง Transaction ใหม่ หรือ return ที่มีอยู่แล้ว (ถ้ายังไม่หมดอายุ)
        """
        expire_min = getattr(settings, "PAYMENTS_EXPIRE_MINUTES", 15)
        expire_at = timezone.now() + timedelta(minutes=expire_min)

        tx = (
            Transaction.objects.select_for_update()
            .filter(user=user, payment_status="pending")
            .first()
        )

        if tx:
            if tx.expire_at and tx.expire_at < timezone.now():
                tx.payment_status = "expired"
                tx.save(update_fields=["payment_status"])
            else:
                if tx.package_id == package.id:
                    return tx

                tx.package = package
                tx.amount = int(package.price)
                tx.credit_amount = package.credits
                tx.expire_at = expire_at
                tx.stripe_session_id = None

                tx.save(
                    update_fields=[
                        "package",
                        "amount",
                        "credit_amount",
                        "expire_at",
                        "stripe_session_id",
                        "updated_at",
                    ]
                )

                return tx

        ref = uuid.uuid4().hex[:12]

        tx = Transaction.objects.create(
            user=user,
            package=package,
            payment_status="pending",
            payment_ref=ref,
            amount=int(package.price),
            credit_amount=package.credits,
            expire_at=expire_at,
        )

        return tx

    @staticmethod
    def create_checkout(transaction_id: int) -> dict:
        tx = Transaction.objects.get(id=transaction_id)

        if tx.payment_status != "pending":
            raise ValueError("Transaction not pending")

        StripeService._init()

        if tx.stripe_session_id:
            session = stripe.checkout.Session.retrieve(tx.stripe_session_id)

            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }

        result = StripeService.create_checkout_session(tx)

        tx.stripe_session_id = result["session_id"]
        tx.save(update_fields=["stripe_session_id"])

        return result

    @staticmethod
    @transaction.atomic
    def mark_success(transaction_id: int):
        """
        Mark transaction ว่าชำระเงินสำเร็จ (เรียกจาก Admin หรือ Webhook)
        """
        tx = Transaction.objects.select_for_update().get(id=transaction_id)

        if tx.expire_at and tx.expire_at < timezone.now():
            tx.payment_status = "expired"
            tx.save(update_fields=["payment_status"])
            raise ValueError("Transaction expired")

        if tx.payment_status != "pending":
            raise ValueError("Transaction already processed")

        tx.payment_status = "success"
        tx.save(update_fields=["payment_status", "updated_at"])

        wallet, _ = UserCredit.objects.get_or_create(user=tx.user)
        wallet = UserCredit.objects.select_for_update().get(pk=wallet.pk)
        wallet.add_credit(tx.credit_amount)

        CreditLog.objects.create(
            user=tx.user,
            transaction=tx,
            type="topup",
            amount=Decimal(tx.credit_amount),
        )

        return tx

    @staticmethod
    @transaction.atomic
    def mark_success_by_session(session_id: str):

        tx = Transaction.objects.get(stripe_session_id=session_id)
        return PaymentService.mark_success(tx.id)
