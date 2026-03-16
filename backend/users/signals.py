from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import User, UserCredit
from payments.models import CreditLog


@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):

    if not created:
        return

    with transaction.atomic():

        wallet, wallet_created = UserCredit.objects.get_or_create(
            user=instance,
            defaults={"available": 300},
        )

        if wallet_created:
            CreditLog.objects.create(
                user=instance,
                type="topup",
                amount=300,
            )
