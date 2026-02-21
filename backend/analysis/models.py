# from django.utils import timezone
# from django.db import models, transaction
# from novels.models import Novel, Chapter

# from django.core.exceptions import ValidationError

# from users.models import UserCredit
# from payments.models import CreditLog

# class AnalysisSession(models.Model):
#     novel = models.ForeignKey(
#         Novel, on_delete=models.CASCADE, related_name='analysis_sessions'
#     )
#     chapters = models.ManyToManyField(Chapter, related_name='analysis_sessions')

#     name = models.CharField(max_length=255, blank=True)

#     locked_credits = models.FloatField(default=0.0)

#     analyze_credits = models.PositiveIntegerField(default=0)
#     generate_credits = models.PositiveIntegerField(default=0)
#     total_credits = models.PositiveIntegerField(default=0)

#     analysis_progress = models.FloatField(default=0.0)   # 0–100
#     generation_progress = models.FloatField(default=0.0) # 0–100

#     STATUS_CHOICES = (
#         ('draft', 'Draft'),
#         ('analyzing', 'Analyzing'),
#         ('analyzed', 'Analyzed'),
#         ('generating', 'Generating'),
#         ('generated', 'Generated'),
#         ('failed', 'Failed'),
#     )
#     status = models.CharField(
#         max_length=20, choices=STATUS_CHOICES, default='draft'
#     )

#     created_at = models.DateTimeField(auto_now_add=True)
#     finished_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"Session#{self.id} | {self.name}"
    
#     def start_analysis(self):
#         if self.status not in ['draft', 'failed']:
#             raise ValidationError(
#                 f"Cannot start analysis when status = {self.status}"
#             )
        
#         with transaction.atomic():
#             wallet = UserCredit.objects.select_for_update().get(
#                 user=self.novel.user
#             )

#             if wallet.available < self.analyze_credits:
#                 raise ValidationError("Not enough credits")

#             wallet.available -= self.analyze_credits
#             wallet.locked += self.analyze_credits
#             wallet.save(update_fields=['available', 'locked'])

#             self.locked_credits = self.analyze_credits
#             self.status = 'analyzing'
#             self.analysis_progress = 0
#             self.save(update_fields=['status', 'analysis_progress', 'locked_credits'])
        
#     def complete_analysis(self):
#         if self.status != 'analyzing':
#             raise ValidationError(
#                 f"Cannot complete analysis when status = {self.status}"
#             )
            
#         with transaction.atomic():
#             wallet = UserCredit.objects.select_for_update().get(
#                 user=self.novel.user
#             )

#             wallet.locked -= self.locked_credits
#             wallet.used += self.locked_credits
#             wallet.save(update_fields=['locked', 'used'])

#             CreditLog.objects.create(
#                 transaction=self.novel.user.transactions.filter(
#                     payment_status='success'
#                 ).latest('create_at'),
#                 usage_type='analyze',
#                 credit_spend=self.locked_credits
#             )

#             self.locked_credits = 0
#             self.status = 'analyzed'
#             self.analysis_progress = 100
#             self.finished_at = timezone.now()
#             self.save(update_fields=['status', 'analysis_progress', 'locked_credits'])
        
#     def start_generation(self):
#         if self.status != 'analyzed':
#             raise ValidationError(
#                 f"Cannot start generation when status = {self.status}"
#             )

#         with transaction.atomic():
#             wallet = UserCredit.objects.select_for_update().get(
#                 user=self.novel.user
#             )

#             if wallet.available < self.generate_credits:
#                 raise ValidationError("Not enough credits")

#             wallet.available -= self.generate_credits
#             wallet.locked += self.generate_credits
#             wallet.save(update_fields=['available', 'locked'])

#             CreditLog.objects.create(
#                 user=self.novel.user,
#                 session=self,
#                 type='generation_lock',
#                 credit_amount=self.generate_credits
#             )

#             self.locked_credits = self.generate_credits
#             self.status = 'generating'
#             self.generation_progress = 0
#             self.save(update_fields=[
#                 'status',
#                 'generation_progress',
#                 'locked_credits'
#             ])

#     def complete_generation(self):
#         if self.status != 'generating':
#             raise ValidationError(
#                 f"Cannot complete generation when status = {self.status}"
#             )
            
#         with transaction.atomic():
#             wallet = UserCredit.objects.select_for_update().get(
#                 user=self.novel.user
#             )

#             wallet.locked -= self.locked_credits
#             wallet.used += self.locked_credits
#             wallet.save(update_fields=['locked', 'used'])

#             CreditLog.objects.create(
#                 user=self.novel.user,
#                 session=self,
#                 type='generation_complete',
#                 credit_amount=self.locked_credits
#             )

#             self.locked_credits = 0
#             self.status = 'generated'
#             self.generation_progress = 100
#             self.finished_at = timezone.now()
#             self.save(update_fields=[
#                 'status',
#                 'generation_progress',
#                 'locked_credits',
#                 'finished_at'
#             ])
        
#     def fail(self, error_msg=None):
#         with transaction.atomic():
#             if self.locked_credits > 0:
#                 wallet = UserCredit.objects.select_for_update().get(
#                     user=self.novel.user
#                 )
#                 wallet.locked -= self.locked_credits
#                 wallet.available += self.locked_credits
#                 wallet.save(update_fields=['locked', 'available'])

#         self.locked_credits = 0
#         self.status = 'failed'
#         self.finished_at = timezone.now()
#         self.save(update_fields=[
#             'status', 'locked_credits', 'finished_at'
#         ])

#         step = self.process_step.filter(status='processing').last()
#         if step:
#             step.fail_step(error_msg)
        
#     def update_analysis_progress(self):
#         total = self.process_step.filter(phase='analysis').count()
#         done = self.process_step.filter(
#             phase='analysis',
#             status='success'
#         ).count()
#         self.analysis_progress = (done / total) * 100 if total else 0
#         self.save(update_fields=['analysis_progress'])
        
#     def update_generation_progress(self):
#         total = self.process_step.filter(phase='generation').count()
#         done = self.process_step.filter(
#             phase='generation',
#             status='success'
#         ).count()
#         self.generation_progress = (done / total) * 100 if total else 0
#         self.save(update_fields=['generation_progress'])
    
#     def progress_percent(self):
#         total = self.analysis_session.process_step.count()
#         done = self.analysis_session.process_step.filter(
#             status__in=['success', 'failed']
#         ).count()
#         return (done / total) * 100 if total else 0
            
# class CharacterProfileAnalysis(models.Model):
#     novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='character_profiles')
#     external_id = models.CharField(max_length=50, null=True, blank=True)
#     name = models.CharField(max_length=100, null=True, blank=True)
#     appearance = models.TextField(null=True, blank=True)
#     outfit = models.TextField(null=True, blank=True)
#     sex = models.CharField(max_length=20, null=True, blank=True)
#     age = models.CharField(max_length=20, null=True, blank=True)
#     race = models.CharField(max_length=50, null=True, blank=True)
#     base_personality = models.TextField(null=True, blank=True)
#     master_image_path = models.FileField(null=True, blank=True)
#     master_voice_path = models.FileField(null=True, blank=True)
    
#     def __str__(self):
#         return f"{self.name or 'Narrator'} ({self.novel.title})"
    
#     class Meta:
#         unique_together = ('novel', 'name')

# class SentenceAnalysis(models.Model):
#     analysis_session = models.ForeignKey(
#         AnalysisSession, 
#         on_delete=models.CASCADE, 
#         related_name='sentences'
#     )
#     sentence_index = models.PositiveIntegerField(default=1)
#     chapter = models.ForeignKey(
#         Chapter, 
#         on_delete=models.CASCADE, 
#         null=True, 
#         blank=True
#     )
#     character_profile = models.ForeignKey(
#         CharacterProfileAnalysis, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True, 
#         related_name='sentences'
#     )
#     character_name = models.CharField(max_length=100, blank=True)
#     TYPE_CHOICES = (
#         ('narration', 'Narration'),
#         ('dialogue', 'Dialogue'),
#     )
#     type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='narration', blank=True)
#     emotion = models.CharField(max_length=20, blank=True)
#     sentence = models.TextField(blank=True)
    
#     def __str__(self):
#         return f"S{self.sentence_index} | {self.type} | {self.character_name or 'Narrator'}"
#     class Meta:
#         unique_together = ('analysis_session', 'chapter', 'sentence_index')
    
# class IllustrationAnalysis(models.Model):
#     analysis_session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='illustrations')
#     chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
#     positive_prompt = models.TextField(null=True, blank=True)
#     negative_prompt = models.TextField(null=True, blank=True)
    
#     def __str__(self):
#         return f"Illustration | {self.chapter.title}"
    
#     class Meta:
#         unique_together = ('analysis_session', 'chapter')
    
# class ProcessingStep(models.Model):
#     analysis_session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='process_step')
#     PHASE_CHOICES = (
#         ('analysis', 'Data Analysis Phase'),
#         ('generation', 'Video Generation Phase',)
#     )
#     phase = models.CharField(max_length=50, choices=PHASE_CHOICES, default='analysis')
#     STEP_NAME_CHOICES = (
#         ('text_analysis', 'Text Analysis'),
#         ('character_extraction', 'Character Extraction'),
#         ('illustration_gen', 'Illustration Prompt Generation'),
#         ('voice_gen', 'Voice Synthesis'),
#         ('image_gen', 'Image Generation'),
#         ('video_compilation', 'Video Compilation'),
#     )
#     name = models.CharField(max_length=30, choices=STEP_NAME_CHOICES)
#     order = models.PositiveBigIntegerField(default=1)
#     STATUS_CHOICES = (
#         ('pending', 'Pending'),
#         ('processing', 'Processing'),
#         ('success', 'Success'),
#         ('failed', 'Failed'),
#     )
#     status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
#     is_read = models.BooleanField(default=False)
#     error_message = models.TextField(null=True, blank=True)
#     start_at = models.DateTimeField(null=True, blank=True)
#     finish_at = models.DateTimeField(null=True, blank=True)
    
#     def __str__(self):
#         return f"{self.get_name_display()} | {self.get_phase_display()} | {self.get_status_display()}"
    
#     class Meta:
#         ordering = ['phase', 'order']
        
#     def start_step(self):
#         self.status = 'processing'
#         self.start_at = timezone.now()
#         self.save()
        
#     def fail_step(self, error_msg):
#         self.status = 'failed'
#         self.error_message = error_msg
#         self.finish_at = timezone.now()
#         self.save()
        
#     def complete_step(self):
#         self.status = 'success'
#         self.finish_at = timezone.now()
#         self.save()
        
#     def is_done(self):
#         return self.status in ['success', 'failed']
    