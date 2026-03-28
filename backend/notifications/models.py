from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Notification(models.Model):

    TASK_TYPE_CHOICES = (
        ("analysis", "Analysis"),
        ("generation", "Generation"),
        ("upload", "Upload"),
        ("fix_text", "Fix Text"),
    )

    STATUS_CHOICES = (
        ("processing", "Processing"),
        ("success", "Success"),
        ("error", "Error"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    session = models.ForeignKey(
        "ngenerate_sessions.Session",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    generation_run = models.ForeignKey(
        "ngenerate_sessions.GenerationRun",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    novel = models.ForeignKey(
        "novels.Novel",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    task_type = models.CharField(
        max_length=20, choices=TASK_TYPE_CHOICES, null=True, blank=True
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="processing"
    )

    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    file_path = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "task_type"],
                condition=models.Q(task_type="analysis"),
                name="unique_session_analysis_notification",
            ),
            models.UniqueConstraint(
                fields=["generation_run"],
                condition=models.Q(task_type="generation"),
                name="unique_generation_run_notification",
            ),
        ]
        indexes = [
            models.Index(fields=["session", "task_type"]),
            models.Index(fields=["generation_run"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        if self.generation_run:
            return f"{self.user} | generation v{self.generation_run.version}"
        return f"{self.user} | {self.task_type}"

    def clean(self):
        if not self.session and not self.novel:
            raise ValidationError("Notification must relate to session or novel")

        if self.session and self.novel:
            raise ValidationError(
                "Notification cannot relate to both session and novel"
            )

        if self.task_type == "generation" and self.session and not self.generation_run:
            raise ValidationError("Generation notification must have a generation_run")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_effective_status(self):
        if self.task_type == "analysis" and self.session:
            if self.session.status not in ("analyzed", "failed"):
                return "processing"
            if self.session.status == "failed":
                return "error"

            steps = self.session.processing_steps.filter(phase="analysis")
            if not steps.exists():
                return self.status
            if steps.filter(status="failed").exists():
                return "error"
            if steps.filter(status__in=["processing", "pending"]).exists():
                return "processing"
            return "success"

        if self.task_type == "generation" and self.generation_run:
            if self.generation_run.status not in ("generated", "failed"):
                return "processing"
            if self.generation_run.status == "failed":
                return "error"

            steps = self.generation_run.processing_steps.all()
            if not steps.exists():
                return self.status
            if steps.filter(status="failed").exists():
                return "error"
            if steps.filter(status__in=["processing", "pending"]).exists():
                return "processing"
            return "success"

        return self.status
