from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Notification(models.Model):

    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('error', 'Error'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # งาน session
    session = models.ForeignKey(
        'ngenerate_sessions.Session',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )

    # งาน upload novel
    novel = models.ForeignKey(
        'novels.Novel',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )

    task_name = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing'
    )

    message = models.TextField(blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user} | {self.task_name}"

    def clean(self):
        if not self.session and not self.novel:
            raise ValidationError("Notification must relate to session or novel")

        if self.session and self.novel:
            raise ValidationError("Notification cannot relate to both session and novel")
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
    def get_effective_status(self):
        if not self.session:
            return self.status

        steps = self.session.processing_steps.all()

        if not steps.exists():
            return "processing"

        if steps.filter(status="failed").exists():
            return "error"

        if steps.filter(status="processing").exists():
            return "processing"

        if steps.filter(status="pending").exists():
            return "processing"

        return "success"