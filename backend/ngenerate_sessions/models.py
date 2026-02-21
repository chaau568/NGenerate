from django.utils import timezone
from django.db import models, transaction
from django.core.exceptions import ValidationError
from novels.models import Novel, Chapter
from users.models import UserCredit
from payments.models import CreditLog
from notifications.models import Notification
from .pricing import CreditPricing

class Session(models.Model):

    SESSION_TYPE_CHOICES = (
        ('analysis', 'Analysis Only'),
        ('full', 'Analysis + Generation'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
    )
    
    STYLE_CHOICES = (
        ('chinese', 'Chinese'),
        ('japanese', 'Japanese'),
        ('futuristic', 'Futuristic'),
        ('medieval', 'Medieval'),
        ('ghibli', 'Ghibli'),
    )

    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    chapters = models.ManyToManyField(
        Chapter,
        related_name='sessions'
    )
    
    name = models.CharField(max_length=255, blank=True)

    session_type = models.CharField(
        max_length=50,
        choices=SESSION_TYPE_CHOICES,
        default='analysis'
    )
    
    style = models.CharField(
        max_length=50, 
        choices=STYLE_CHOICES, 
        default='ghibli'
    )

    # credit tracking
    analyze_credits = models.PositiveIntegerField(default=0)
    generate_credits = models.PositiveIntegerField(default=0)
    locked_credits = models.PositiveIntegerField(default=0)

    # flags
    is_analysis_done = models.BooleanField(default=False)
    is_generation_done = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    analysis_finished_at = models.DateTimeField(null=True, blank=True)
    generation_finished_at = models.DateTimeField(null=True, blank=True)
    
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

        character_count = self.novel.character_profiles.count()
        character_credit = character_count * CreditPricing.CHARACTER_IMAGE

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

            if session.status not in ['draft', 'failed']:
                raise ValidationError("Cannot start analysis")

            if session.locked_credits > 0:
                raise ValidationError("Session already has locked credits")

            required_credit = session.calculate_analysis_credit()

            wallet = UserCredit.objects.select_for_update().get(
                user=session.novel.user
            )

            if wallet.available < required_credit:
                raise ValidationError("Not enough credits")

            wallet.available -= required_credit
            wallet.save(update_fields=["available"])

            session.locked_credits = required_credit
            session.status = 'analyzing'
            session.save(update_fields=["locked_credits", "status"])
            
            Notification.objects.create(
                user=self.novel.user,
                session=self,
                task_name="Analysis",
                status='processing',
                message=f"Starting analysis for {self.name}"
            )

            CreditLog.objects.create(
                user=session.novel.user,
                session=session,
                type='analysis_lock',
                amount=-required_credit
            )

    def complete_analysis(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.status != 'analyzing':
                raise ValidationError("Invalid state")

            CreditLog.objects.create(
                user=session.novel.user,
                session=session,
                type='analysis_complete',
                amount=0
            )

            session.locked_credits = 0
            session.status = 'analyzed'
            session.is_analysis_done = True
            session.analysis_finished_at = timezone.now()

            session.save(update_fields=[
                "locked_credits",
                "status",
                "is_analysis_done",
                "analysis_finished_at"
            ])
            
            Notification.objects.create(
                user=self.novel.user,
                session=self,
                task_name="Analysis",
                status='success',
                message=f"Analysis completed for {self.name}"
            )

    # =====================================================
    # GENERATION FLOW
    # =====================================================

    def start_generation(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.session_type != 'full':
                raise ValidationError("This session does not allow generation")

            if not session.is_analysis_done:
                raise ValidationError("Analysis not completed")

            if session.status != 'analyzed':
                raise ValidationError("Invalid state")

            if session.locked_credits > 0:
                raise ValidationError("Session already has locked credits")

            required_credit = session.calculate_generation_credit()

            wallet = UserCredit.objects.select_for_update().get(
                user=session.novel.user
            )

            if wallet.available < required_credit:
                raise ValidationError("Not enough credits")

            wallet.available -= required_credit
            wallet.save(update_fields=["available"])

            session.locked_credits = required_credit
            session.status = 'generating'

            session.save(update_fields=["locked_credits", "status"])

            CreditLog.objects.create(
                user=session.novel.user,
                session=session,
                type='generation_lock',
                amount=-required_credit
            )
            
            Notification.objects.create(
                user=self.novel.user,
                session=self,
                task_name="Generation",
                status='processing',
                message=f"Starting generation for {self.name}"
            )

    def complete_generation(self):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.status != 'generating':
                raise ValidationError("Invalid state")

            CreditLog.objects.create(
                user=session.novel.user,
                session=session,
                type='generation_complete',
                amount=0
            )

            session.locked_credits = 0
            session.status = 'generated'
            session.is_generation_done = True
            session.generation_finished_at = timezone.now()

            session.save(update_fields=[
                "locked_credits",
                "status",
                "is_generation_done",
                "generation_finished_at"
            ])
            
            Notification.objects.create(
                user=self.novel.user,
                session=self,
                task_name="Generation",
                status='success',
                message=f"Generation completed for {self.name}"
            )

    # =====================================================
    # FAIL / REFUND
    # =====================================================

    def fail(self, error_msg=None):

        with transaction.atomic():

            session = Session.objects.select_for_update().get(pk=self.pk)

            if session.locked_credits > 0:

                wallet = UserCredit.objects.select_for_update().get(
                    user=session.novel.user
                )

                wallet.available += session.locked_credits
                wallet.save(update_fields=["available"])

                CreditLog.objects.create(
                    user=session.novel.user,
                    session=session,
                    type='refund',
                    amount=session.locked_credits
                )

            session.locked_credits = 0
            session.status = 'failed'

            session.save(update_fields=["locked_credits", "status"])
            
            Notification.objects.create(
                user=self.novel.user,
                session=self,
                task_name=f"{self.status.capitalize()} Failed",
                status='error',
                message=error_msg or f"An error occurred during {self.status}"
            )
            
    # =====================================================
    # PROGRESSING CONTROL
    # =====================================================
            
    def get_progress_percentage(self):
        steps = self.processing_steps.all()
        total = steps.count()
        
        if total == 0:
            return 0
        
        success_count = steps.filter(status='success').count()
        return int((success_count / total) * 100)
    
    def update_notification_progress(self):

        notification = self.notifications.filter(status="processing").last()

        if not notification:
            return

        progress = self.get_progress_percentage()

        notification.message = (
            f"{notification.task_name} in progress... {progress}% completed."
        )
        notification.save(update_fields=["message", "updated_at"])
    
    def create_processing_steps(self, phase):

        steps_config = {
            'analysis': [
                (1, 'Character Identification'),
                (2, 'Scene Segmentation'),
                (3, 'Sentence Structuring'),
            ],
            'generation': [
                (1, 'Generating Image Prompts'),
                (2, 'Image Creation'),
                (3, 'Voice Synthesis'),
                (4, 'Generating Video'),
            ]
        }

        new_steps = []
        for order, name in steps_config.get(phase, []):
            step, _ = ProcessingStep.objects.get_or_create(
                session=self,
                phase=phase,
                name=name,
                defaults={'order': order, 'status': 'pending'}
            )
            new_steps.append(step)

        return new_steps


    def get_next_pending_step(self, phase):
        return self.processing_steps.filter(
            phase=phase,
            status='pending'
        ).order_by('order').first()
            
class CharacterProfile(models.Model):

    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='character_profiles'
    )

    external_id = models.CharField(max_length=50, null=True, blank=True)

    name = models.CharField(max_length=100)
    appearance = models.TextField(blank=True)
    outfit = models.TextField(blank=True)
    sex = models.CharField(max_length=20, blank=True)
    age = models.CharField(max_length=20, blank=True)
    race = models.CharField(max_length=50, blank=True)
    base_personality = models.TextField(blank=True)

    master_image_path = models.FileField(null=True, blank=True)
    master_voice_path = models.FileField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('novel', 'name')

    def __str__(self):
        return f"{self.name} ({self.novel.title})"
        
class Character(models.Model):

    profile = models.ForeignKey(
        CharacterProfile,
        on_delete=models.CASCADE,
        related_name='characters'
    )

    emotion = models.CharField(max_length=50)

    positive_prompt = models.TextField()
    negative_prompt = models.TextField(blank=True)

    image_path = models.FileField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'emotion')
        
class Sentence(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='sentences'
    )

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE
    )

    sentence_index = models.PositiveIntegerField()

    character = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sentences'
    )

    TYPE_CHOICES = (
        ('narration', 'Narration'),
        ('dialogue', 'Dialogue'),
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='narration'
    )

    sentence = models.TextField()
    emotion = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('session', 'chapter', 'sentence_index')
        
class Illustration(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='illustrations'
    )

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE
    )

    positive_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)

    class Meta:
        unique_together = ('session', 'chapter')
        
class ProcessingStep(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='processing_steps'
    )

    PHASE_CHOICES = (
        ('analysis', 'Analysis'),
        ('generation', 'Generation'),
    )

    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)

    name = models.CharField(max_length=50)

    order = models.PositiveIntegerField(default=1)

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    error_message = models.TextField(blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['phase', 'order']
        
    def mark_start(self):
        self.status = 'processing'
        self.start_at = timezone.now()
        self.save(update_fields=['status', 'start_at'])

    def mark_success(self):
        self.status = 'success'
        self.finish_at = timezone.now()
        self.save(update_fields=['status', 'finish_at'])

    def mark_failed(self, error_msg):
        self.status = 'failed'
        self.error_message = error_msg
        self.finish_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'finish_at'])
