from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserCredit


@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        UserCredit.objects.create(user=instance)
