from django.db import transaction
from users.models import UserCredit
from payments.models import CreditLog
from django.db.models import F


class CreditService:

    @staticmethod
    @transaction.atomic
    def lock_credit(user, amount, session, log_type):

        wallet = UserCredit.objects.select_for_update().get(user=user)

        if wallet.available < amount:
            raise ValueError("Not enough credits")

        wallet.available = F("available") - amount
        wallet.save(update_fields=["available"])

        CreditLog.objects.create(
            user=user,
            session=session,
            type=log_type,
            amount=-amount,
        )

    @staticmethod
    @transaction.atomic
    def refund_credit(user, amount, session):

        wallet = UserCredit.objects.select_for_update().get(user=user)

        wallet.available = F("available") + amount
        wallet.save(update_fields=["available"])

        CreditLog.objects.create(
            user=user,
            session=session,
            type="refund",
            amount=amount,
        )
