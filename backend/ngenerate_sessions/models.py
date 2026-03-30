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
        ("failed", "Failed"),
    )

    STYLE_CHOICES = (
        # ("ghibli", "Ghibli"),
        ("chinese", "Chinese Oil Painting"),
        ("chinese-modern", "Chinese Modern (Xianxia)"),
        ("fantasy", "Fantasy"),
        ("medieval", "Medieval"),
        ("futuristic", "Futuristic"),
    )

    NARRATOR_VOICE_CHOICES = (
        ("man1", "Man 1"),
        # ("man2", "Man 2"),
        # ("girl1", "Girl 1"),
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
    narrator_voice = models.CharField(
        max_length=20, choices=NARRATOR_VOICE_CHOICES, default="man1"
    )

    analyze_credits = models.PositiveIntegerField(default=0)
    locked_credits = models.PositiveIntegerField(default=0)
    is_analysis_done = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    created_at = models.DateTimeField(auto_now_add=True)
    analysis_finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} | {self.session_type} | {self.style}"

    def save(self, *args, **kwargs):
        if not self.id and not self.name:
            self.name = "New Session"
        super().save(*args, **kwargs)

    # =====================================================
    # HELPERS
    # =====================================================

    def get_latest_generation_run(self):
        return self.generation_runs.order_by("-version").first()

    def get_active_generation_run(self):
        return self.generation_runs.filter(status="generating").first()

    @property
    def is_generation_done(self):
        return self.generation_runs.filter(status="generated").exists()

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

        # ใช้ SceneCharacter แทน Character เดิม
        character_image_count = self.scene_characters.count()
        character_credit = character_image_count * CreditPricing.CHARACTER_IMAGE

        scene_count = self.illustrations.count()
        scene_credit = scene_count * CreditPricing.SCENE_IMAGE

        return sentence_credit + character_credit + scene_credit

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
                    session_name=session.name,
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

            locked = session.locked_credits
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

            CreditService.complete_credit(
                user=session.novel.user,
                amount=locked,
                session=session,
                log_type="analysis_complete",
                session_name=session.name,
            )

            notification = self.notifications.filter(task_type="analysis").first()
            if notification:
                update_notification(
                    notification,
                    status="success",
                    message=f"Analysis completed for '{self.name}'",
                )

    # =====================================================
    # FAIL (ANALYSIS ONLY)
    # =====================================================

    def fail(self, error_msg=None):
        with transaction.atomic():
            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.locked_credits > 0:
                CreditService.refund_credit(
                    user=session.novel.user,
                    amount=session.locked_credits,
                    session=session,
                    session_name=session.name,
                )

            session.locked_credits = 0
            session.status = "failed"
            session.save(update_fields=["locked_credits", "status"])

            notification = self.notifications.filter(
                task_type="analysis", status="processing"
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="error",
                    message=error_msg or "Analysis failed",
                )

    # =====================================================
    # PROGRESS (ANALYSIS PHASE ONLY)
    # =====================================================

    def get_progress_percentage(self):
        if self.status == "analyzed":
            return 100

        if self.current_phase != "analysis":
            return 0

        agg = self.processing_steps.filter(phase="analysis").aggregate(
            total=Count("id"),
            success=Count("id", filter=Q(status="success")),
        )

        total = agg["total"]
        success = agg["success"]

        if total == 0:
            return 0

        return round((success / total) * 100)

    def update_notification_progress(self):
        notification = self.notifications.filter(
            status="processing", task_type="analysis"
        ).first()

        if not notification:
            return

        progress = self.get_progress_percentage()
        notification.message = f"Analysis in progress... {progress}% completed."
        notification.save(update_fields=["message", "updated_at"])

    def create_processing_steps(self, phase):
        self.processing_steps.filter(phase=phase).delete()

        steps_config = {
            "analysis": [
                (1, "Split Sentences"),
                (2, "Identify Characters"),
                (3, "Segment Scenes"),
                (4, "Analyze Sentence Details"),
                (5, "Build Base Structure"),
            ],
        }

        new_steps = []
        for order, name in steps_config.get(phase, []):
            step = ProcessingStep.objects.create(
                session=self, phase=phase, name=name, order=order, status="pending"
            )
            new_steps.append(step)

        return new_steps

    # =====================================================
    # NOTIFICATION CONTROL
    # =====================================================

    def calculate_notification_status(self):
        steps = self.processing_steps.filter(phase="analysis")

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


# =====================================================
# GENERATION RUN
# =====================================================


class GenerationRun(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("generated", "Generated"),
        ("failed", "Failed"),
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="generation_runs",
    )

    version = models.PositiveIntegerField(default=1)
    style = models.CharField(max_length=50, choices=Session.STYLE_CHOICES)
    narrator_voice = models.CharField(
        max_length=20, choices=Session.NARRATOR_VOICE_CHOICES
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    generate_credits = models.PositiveIntegerField(default=0)
    locked_credits = models.PositiveIntegerField(default=0)

    generation_finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "version"],
                name="unique_generation_run_version_per_session",
            )
        ]
        ordering = ["-version"]

    def __str__(self):
        return f"Run v{self.version} | {self.session.name} | {self.status}"

    # =====================================================
    # GENERATION FLOW
    # =====================================================

    @classmethod
    def create_next(cls, session):
        last = session.generation_runs.order_by("-version").first()
        next_version = (last.version + 1) if last else 1
        return cls.objects.create(
            session=session,
            version=next_version,
            style=session.style,
            narrator_voice=session.narrator_voice,
            status="pending",
        )

    def start(self):
        with transaction.atomic():
            run = GenerationRun.objects.select_for_update().get(pk=self.pk)
            session = Session.objects.select_for_update().get(pk=run.session_id)

            if not session.is_analysis_done:
                raise ValidationError("Analysis not completed")

            if session.status != "analyzed":
                raise ValidationError("Session is not in analyzed state")

            if run.status != "pending":
                raise ValidationError("GenerationRun is not in pending state")

            if session.generation_runs.filter(status="generating").exists():
                raise ValidationError("Another generation is already running")

            required_credit = session.calculate_generation_credit()

            try:
                CreditService.lock_credit(
                    user=session.novel.user,
                    amount=required_credit,
                    session=session,
                    log_type="generation_lock",
                    session_name=session.name,
                )
            except ValueError:
                raise ValidationError("Not enough credits")

            run.locked_credits = required_credit
            run.generate_credits = required_credit
            run.status = "generating"
            run.save(update_fields=["locked_credits", "generate_credits", "status"])

            if session.session_type != "full":
                session.session_type = "full"
                session.save(update_fields=["session_type"])

            get_or_create_notification(
                user=session.novel.user,
                session=session,
                generation_run=run,
                task_type="generation",
                message=f"Generating assets for '{session.name}' (v{run.version})...",
            )

    def complete(self):
        with transaction.atomic():
            run = GenerationRun.objects.select_for_update().get(pk=self.pk)

            if run.status != "generating":
                raise ValidationError("Invalid state")

            locked = run.locked_credits
            run.locked_credits = 0
            run.status = "generated"
            run.generation_finished_at = timezone.now()
            run.save(
                update_fields=["locked_credits", "status", "generation_finished_at"]
            )

            session = run.session

            CreditService.complete_credit(
                user=session.novel.user,
                amount=locked,
                session=session,
                log_type="generation_complete",
                session_name=session.name,
            )

            notification = session.notifications.filter(
                task_type="generation",
                generation_run=run,
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="success",
                    message=f"Video generation completed for '{session.name}' (v{run.version})",
                )

    def fail(self, error_msg=None):
        with transaction.atomic():
            run = GenerationRun.objects.select_for_update().get(pk=self.pk)
            session = run.session

            if run.locked_credits > 0:
                CreditService.refund_credit(
                    user=session.novel.user,
                    amount=run.locked_credits,
                    session=session,
                    session_name=session.name,
                )

            run.locked_credits = 0
            run.status = "failed"
            run.save(update_fields=["locked_credits", "status"])

            notification = session.notifications.filter(
                task_type="generation",
                generation_run=run,
                status="processing",
            ).first()

            if notification:
                update_notification(
                    notification,
                    status="error",
                    message=error_msg or f"Generation v{run.version} failed",
                )

    # =====================================================
    # PROGRESS
    # =====================================================

    def get_progress_percentage(self):
        if self.status == "generated":
            return 100

        if self.status != "generating":
            return 0

        agg = self.processing_steps.aggregate(
            total=Count("id"),
            success=Count("id", filter=Q(status="success")),
        )

        total = agg["total"]
        success = agg["success"]

        if total == 0:
            return 0

        return round((success / total) * 100)

    def update_notification_progress(self):
        session = self.session
        notification = session.notifications.filter(
            status="processing",
            task_type="generation",
            generation_run=self,
        ).first()

        if not notification:
            return

        progress = self.get_progress_percentage()
        notification.message = f"Generation in progress... {progress}% completed."
        notification.save(update_fields=["message", "updated_at"])

    def create_processing_steps(self):
        self.processing_steps.all().delete()

        steps_config = [
            (1, "Generating Character Master"),
            (2, "Generating Scenes & Voices"),
            (3, "Generating Character Scenes"),
            (4, "Composing Final Video"),
        ]

        new_steps = []
        for order, name in steps_config:
            step = GenerationProcessingStep.objects.create(
                generation_run=self,
                name=name,
                order=order,
                status="pending",
            )
            new_steps.append(step)

        return new_steps

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

    def sync_notification_status(self):
        session = self.session
        notification = session.notifications.filter(
            task_type="generation",
            generation_run=self,
        ).first()

        if not notification:
            return

        new_status = self.calculate_notification_status()
        if notification.status != new_status:
            notification.status = new_status
            notification.save(update_fields=["status", "updated_at"])


# =====================================================
# CHARACTER PROFILE
# =====================================================


class CharacterProfile(models.Model):

    novel = models.ForeignKey(
        Novel, on_delete=models.CASCADE, related_name="character_profiles"
    )

    name = models.CharField(max_length=100)
    appearance = models.TextField(blank=True)
    appearance_tags = models.TextField(blank=True)
    outfit = models.TextField(blank=True)
    sex = models.CharField(max_length=20, blank=True)
    age = models.CharField(max_length=20, blank=True)
    race = models.CharField(max_length=50, blank=True)
    base_personality = models.TextField(blank=True)
    aliases = models.TextField(blank=True, default="")

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


# =====================================================
# SENTENCE
# ลบ emotion ออก — ไม่ได้ใช้สำหรับ TTS แล้ว
# =====================================================


class Sentence(models.Model):

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="sentences"
    )
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    sentence_index = models.PositiveIntegerField()

    tts_text = models.TextField(blank=True)
    sentence = models.TextField()

    class Meta:
        unique_together = ("session", "chapter", "sentence_index")
        ordering = ["session_id", "chapter_id", "sentence_index"]
        indexes = [
            models.Index(fields=["session", "sentence_index"]),
        ]

    def __str__(self):
        return f"{self.session} | {self.chapter} | {self.sentence_index}"


# =====================================================
# ILLUSTRATION  (scene unit — คงเดิม)
# =====================================================


class Illustration(models.Model):

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="illustrations"
    )
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    scene_index = models.PositiveIntegerField(default=1)
    sentence_start = models.PositiveIntegerField(null=True, blank=True)
    sentence_end = models.PositiveIntegerField(null=True, blank=True)
    scene_description = models.TextField(blank=True)

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "chapter", "scene_index")
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["session", "chapter"]),
        ]

    def __str__(self):
        return f"{self.session} | Ch{self.chapter.order} | Scene {self.scene_index}"

    def get_scene_characters(self):
        """ดึง SceneCharacter ทั้งหมดของฉากนี้ พร้อม profile"""
        return self.scene_characters.select_related("character_profile").all()


# =====================================================
# SCENE CHARACTER  (แทน Character + SentenceCharacter เดิม)
#
# 1 record = 1 ตัวละคร ต่อ 1 ฉาก
# unique_together = (illustration, character_profile)
# =====================================================


class SceneCharacter(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="scene_characters",
    )
    illustration = models.ForeignKey(
        Illustration,
        on_delete=models.CASCADE,
        related_name="scene_characters",
    )
    character_profile = models.ForeignKey(
        CharacterProfile,
        on_delete=models.CASCADE,
        related_name="scene_characters",
    )

    pose = models.CharField(max_length=100, blank=True)
    action = models.CharField(max_length=200, blank=True)
    expression = models.CharField(max_length=100, blank=True)

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    class Meta:
        unique_together = ("illustration", "character_profile")
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["illustration"]),
        ]

    def __str__(self):
        scene_idx = self.illustration.scene_index
        ch_order = self.illustration.chapter.order
        return (
            f"Ch{ch_order} Scene{scene_idx} | "
            f"{self.character_profile.name} | "
            f"{self.action or self.pose or 'idle'}"
        )


# =====================================================
# PROCESSING STEPS
# =====================================================


class ProcessingStep(models.Model):
    """Analysis phase steps — ผูกกับ Session"""

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="processing_steps"
    )

    PHASE_CHOICES = (("analysis", "Analysis"),)

    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default="analysis")
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
        ordering = ["order"]

    def __str__(self):
        return f"[Analysis] {self.name} | {self.status}"

    def mark_start(self):
        self.status = "processing"
        self.start_at = timezone.now()
        self.save(update_fields=["status", "start_at"])
        self.session.sync_notification_status("analysis")

    def mark_success(self):
        self.status = "success"
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "finish_at"])
        self.session.sync_notification_status("analysis")

    def mark_failed(self, error_msg):
        self.status = "failed"
        self.error_message = error_msg
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finish_at"])
        self.session.sync_notification_status("analysis")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class GenerationProcessingStep(models.Model):

    generation_run = models.ForeignKey(
        GenerationRun,
        on_delete=models.CASCADE,
        related_name="processing_steps",
    )

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
        ordering = ["order"]

    def __str__(self):
        return (
            f"[Generation v{self.generation_run.version}] {self.name} | {self.status}"
        )

    def mark_start(self):
        self.status = "processing"
        self.start_at = timezone.now()
        self.save(update_fields=["status", "start_at"])
        self.generation_run.sync_notification_status()

    def mark_success(self):
        self.status = "success"
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "finish_at"])
        self.generation_run.sync_notification_status()

    def mark_failed(self, error_msg):
        self.status = "failed"
        self.error_message = error_msg
        self.finish_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finish_at"])
        self.generation_run.sync_notification_status()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
