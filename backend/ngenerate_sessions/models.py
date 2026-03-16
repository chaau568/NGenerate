from django.utils import timezone
from django.db import models, transaction
from django.core.exceptions import ValidationError
from novels.models import Novel, Chapter
from payments.services.credit_service import CreditService
from .pricing import CreditPricing
from notifications.services import get_or_create_notification, update_notification

from django.conf import settings
from utils.file_url import build_file_url

from django.db.models import Count, Q


class Session(models.Model):

    SESSION_TYPE_CHOICES = (
        ("analysis", "Analysis Only"),
        ("full", "Analysis + Generation"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("analyzing", "Analyzing"),
        ("analyzed", "Analyzed"),
        ("generating", "Generating"),
        ("generated", "Generated"),
        ("failed", "Failed"),
    )

    STYLE_CHOICES = (
        ("chinese", "Chinese"),
        ("japanese", "Japanese"),
        ("futuristic", "Futuristic"),
        ("medieval", "Medieval"),
        ("modern", "Modern"),
        ("ghibli", "Ghibli"),
    )

    NARRATOR_VOICE_CHOICES = (
        ("man1", "Man 1"),
        ("man2", "Man 2"),
        ("girl1", "Girl 1"),
    )

    PHASE_CHOICES = (
        ("analysis", "analysis"),
        ("generation", "generation"),
        ("none", "none"),
    )

    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="sessions")

    chapters = models.ManyToManyField(Chapter, related_name="sessions")

    name = models.CharField(max_length=255, blank=True)

    session_type = models.CharField(
        max_length=50, choices=SESSION_TYPE_CHOICES, default="analysis"
    )

    current_phase = models.CharField(
        max_length=20, choices=PHASE_CHOICES, default="none"
    )

    style = models.CharField(max_length=50, choices=STYLE_CHOICES, default="ghibli")

    # credit tracking
    analyze_credits = models.PositiveIntegerField(default=0)
    generate_credits = models.PositiveIntegerField(default=0)
    locked_credits = models.PositiveIntegerField(default=0)

    # flags
    is_analysis_done = models.BooleanField(default=False)
    is_generation_done = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    narrator_voice = models.CharField(
        max_length=20, choices=NARRATOR_VOICE_CHOICES, default="man1"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    analysis_finished_at = models.DateTimeField(null=True, blank=True)
    generation_finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} | {self.session_type} | {self.style}"

    def save(self, *args, **kwargs):
        if not self.id and not self.name:
            self.name = "New Session"

        super().save(*args, **kwargs)

    # =====================================================
    # CREDIT CALCULATION
    # =====================================================

    def calculate_analysis_credit(self):
        chapter_count = self.chapters.count()
        credit = chapter_count * CreditPricing.CHAPTER_UNIT
        self.analyze_credits = credit
        self.save(update_fields=["analyze_credits"])
        return credit

    def calculate_generation_credit(self):
        sentence_count = self.sentences.count()
        sentence_credit = CreditPricing.sentence_to_credit(sentence_count)

        character_image_count = self.characters.count()
        character_credit = character_image_count * CreditPricing.CHARACTER_IMAGE

        scene_count = self.illustrations.count()
        scene_credit = scene_count * CreditPricing.SCENE_IMAGE

        total = sentence_credit + character_credit + scene_credit

        self.generate_credits = total
        self.save(update_fields=["generate_credits"])

        return total

    # =====================================================
    # ANALYSIS FLOW
    # =====================================================

    def start_analysis(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.status not in ["draft", "failed"]:
                raise ValidationError("Cannot start analysis")

            if session.locked_credits > 0:
                raise ValidationError("Session already has locked credits")

            required_credit = session.calculate_analysis_credit()

            try:
                CreditService.lock_credit(
                    user=session.novel.user,
                    amount=required_credit,
                    session=session,
                    log_type="analysis_lock",
                )
            except ValueError:
                raise ValidationError("Not enough credits")

            session.locked_credits = required_credit
            session.status = "analyzing"
            session.current_phase = "analysis"
            session.save(update_fields=["locked_credits", "status", "current_phase"])

            get_or_create_notification(
                user=self.novel.user,
                session=self,
                task_type="analysis",
                message=f"Analyzing session '{self.name}'...",
            )

    def complete_analysis(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            session.chapters.update(is_analyzed=True)

            session.locked_credits = 0
            session.status = "analyzed"
            session.current_phase = "none"
            session.is_analysis_done = True
            session.analysis_finished_at = timezone.now()

            session.save(
                update_fields=[
                    "locked_credits",
                    "status",
                    "current_phase",
                    "is_analysis_done",
                    "analysis_finished_at",
                ]
            )

            notification = self.notifications.filter(
                task_type="analysis", status="processing"
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="success",
                    message=f"Analysis completed for '{self.name}'",
                )

    # =====================================================
    # GENERATION FLOW
    # =====================================================

    def start_generation(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if not session.is_analysis_done:
                raise ValidationError("Analysis not completed")

            if session.status != "analyzed":
                raise ValidationError("Invalid state")

            if session.locked_credits > 0:
                raise ValidationError("Session already has locked credits")

            required_credit = session.calculate_generation_credit()

            try:
                CreditService.lock_credit(
                    user=session.novel.user,
                    amount=required_credit,
                    session=session,
                    log_type="generation_lock",
                )
            except ValueError:
                raise ValidationError("Not enough credits")

            session.locked_credits = required_credit
            session.status = "generating"
            session.current_phase = "generation"

            if session.session_type != "full":
                session.session_type = "full"

            session.save(
                update_fields=[
                    "locked_credits",
                    "status",
                    "session_type",
                    "current_phase",
                ]
            )

            get_or_create_notification(
                user=self.novel.user,
                session=self,
                task_type="generation",
                message=f"Generating assets for '{self.name}'...",
            )

    def complete_generation(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.status != "generating":
                raise ValidationError("Invalid state")

            session.locked_credits = 0
            session.status = "generated"
            session.current_phase = "none"
            session.is_generation_done = True
            session.generation_finished_at = timezone.now()

            session.save(
                update_fields=[
                    "locked_credits",
                    "status",
                    "current_phase",
                    "is_generation_done",
                    "generation_finished_at",
                ]
            )

            notification = self.notifications.filter(
                task_type="generation", status="processing"
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="success",
                    message=f"Video generation completed for '{self.name}'",
                )

    # =====================================================
    # FAIL / REFUND
    # =====================================================

    def fail(self, error_msg=None):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.locked_credits > 0:

                CreditService.refund_credit(
                    user=session.novel.user,
                    amount=session.locked_credits,
                    session=session,
                )

            session.locked_credits = 0
            session.status = "failed"

            session.save(update_fields=["locked_credits", "status"])

            notification = self.notifications.filter(
                task_type__in=["analysis", "generation"], status="processing"
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="error",
                    message=error_msg
                    or f"{notification.task_type.capitalize()} failed",
                )

    # =====================================================
    # RETRY
    # =====================================================

    def reset(self):
        self.status = "pending"
        self.error_message = ""
        self.start_at = None
        self.finish_at = None
        self.save(update_fields=["status", "error_message", "start_at", "finish_at"])

    # =====================================================
    # PROGRESSING CONTROL
    # =====================================================

    def get_progress_percentage(self):

        if self.current_phase == "none":
            return 0

        steps = self.processing_steps.filter(phase=self.current_phase)

        agg = steps.aggregate(
            total=Count("id"), success=Count("id", filter=Q(status="success"))
        )

        total = agg["total"]
        success = agg["success"]

        if total == 0:
            return 0

        return round((success / total) * 100)

    def update_notification_progress(self):

        notification = self.notifications.filter(
            status="processing", task_type__in=["analysis", "generation"]
        ).first()

        if not notification:
            return

        progress = self.get_progress_percentage()

        notification.message = f"{notification.task_type.capitalize()} in progress... {progress}% completed."
        notification.save(update_fields=["message", "updated_at"])

    def create_processing_steps(self, phase):

        self.processing_steps.filter(phase=phase).delete()

        steps_config = {
            "analysis": [
                (1, "Analysis Character"),
                (2, "Analysis Sentence"),
                (3, "Analysis Scene"),
            ],
            "generation": [
                (1, "Generating Character Master Image"),
                (2, "Generating Character Emotion Image"),
                (3, "Generating Scene Image"),
                (4, "Generating Narrator Voice"),
                (5, "Composite Video"),
            ],
        }

        new_steps = []
        for order, name in steps_config.get(phase, []):
            step, _ = ProcessingStep.objects.create(
                session=self, phase=phase, name=name, order=order, status="pending"
            )
            new_steps.append(step)

        return new_steps

    # =====================================================
    # NOTIFICATION CONTROL
    # =====================================================

    def calculate_notification_status(self):
        steps = self.processing_steps.all()

        if not steps.exists():
            return "processing"

        if steps.filter(status="failed").exists():
            return "error"

        if steps.filter(status="processing").exists():
            return "processing"

        if steps.filter(status="pending").exists():
            return "processing"

        return "success"

    def sync_notification_status(self, task_type):

        notification = self.notifications.filter(task_type=task_type).first()

        if not notification:
            return

        new_status = self.calculate_notification_status()

        if notification.status != new_status:
            notification.status = new_status
            notification.save(update_fields=["status", "updated_at"])

    # =====================================================
    # STYLE
    # =====================================================

    def get_style_choices(self):
        return [{"value": value, "label": label} for value, label in self.STYLE_CHOICES]


class CharacterProfile(models.Model):

    novel = models.ForeignKey(
        Novel, on_delete=models.CASCADE, related_name="character_profiles"
    )

    name = models.CharField(max_length=100)
    appearance = models.TextField(blank=True)
    outfit = models.TextField(blank=True)
    sex = models.CharField(max_length=20, blank=True)
    age = models.CharField(max_length=20, blank=True)
    race = models.CharField(max_length=50, blank=True)
    base_personality = models.TextField(blank=True)

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("novel", "name")
        indexes = [
            models.Index(fields=["novel"]),
        ]

    def __str__(self):
        return f"{self.novel.title} ({self.name})"

    def get_master_image_url(self):
        if hasattr(self, "asset") and self.asset.image:
            return build_file_url(self.asset.image)

        return build_file_url("assets/defaults/default_avatar.jpg")


class Sentence(models.Model):

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="sentences"
    )

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    sentence_index = models.PositiveIntegerField()

    sentence = models.TextField()
    emotion = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("session", "chapter", "sentence_index")
        ordering = ["session_id", "chapter_id", "sentence_index"]
        indexes = [
            models.Index(fields=["session", "sentence_index"]),
        ]

    def __str__(self):
        return f"{self.session} | {self.chapter} | {self.sentence_index}"


class Character(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="characters",
    )

    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="characters"
    )

    character_profile = models.ForeignKey(
        CharacterProfile, on_delete=models.CASCADE, related_name="characters"
    )

    emotion = models.CharField(max_length=50)

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "chapter", "character_profile", "emotion")

    def __str__(self):
        return f"{self.chapter} | {self.character_profile.name} | {self.emotion}"


class SentenceCharacter(models.Model):

    sentence = models.ForeignKey(
        Sentence, on_delete=models.CASCADE, related_name="sentence_characters"
    )

    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="sentence_characters"
    )

    class Meta:
        unique_together = ("sentence", "character")
        indexes = [
            models.Index(fields=["sentence"]),
            models.Index(fields=["character"]),
        ]

    def __str__(self):
        return f"{self.sentence} | {self.character.character_profile.name}"


class Illustration(models.Model):

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="illustrations"
    )

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "chapter")
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"{self.session} | {self.chapter}"


class ProcessingStep(models.Model):

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="processing_steps"
    )

    PHASE_CHOICES = (
        ("analysis", "Analysis"),
        ("generation", "Generation"),
    )

    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)

    name = models.CharField(max_length=50)

    order = models.PositiveIntegerField(default=1)

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    error_message = models.TextField(blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["phase", "order"]

    def __str__(self):
        return f"{self.name} | {self.status}"

    def mark_start(self):
        self.status = "processing"
        self.start_at = timezone.now()
        self.save(update_fields=["status", "start_at"])
        self.session.sync_notification_status(self.phase)

    def mark_success(self):
        self.status = "success"
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "finish_at"])
        self.session.sync_notification_status(self.phase)

    def mark_failed(self, error_msg):
        self.status = "failed"
        self.error_message = error_msg
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finish_at"])
        self.session.sync_notification_status(self.phase)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
