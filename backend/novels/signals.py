from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Chapter, Novel


@receiver(post_save, sender=Chapter)
def update_novel_updated_at_on_save(sender, instance, **kwargs):
    Novel.objects.filter(id=instance.novel_id).update(updated_at=timezone.now())


@receiver(post_delete, sender=Chapter)
def update_novel_updated_at_on_delete(sender, instance, **kwargs):
    Novel.objects.filter(id=instance.novel_id).update(updated_at=timezone.now())
