# import os
# from django.db import models
# from analysis.models import AnalysisSession, SentenceAnalysis, IllustrationAnalysis, CharacterProfileAnalysis

# def get_user_asset_path(instance, filename, asset_type):
#     user_id = None
#     try:
#         # ใช้การเช็คแบบไล่ระดับที่ปลอดภัยขึ้น
#         if hasattr(instance, 'sentence') and instance.sentence:
#             user_id = instance.sentence.analysis_session.novel.user.id
#         elif hasattr(instance, 'illustration') and instance.illustration:
#             user_id = instance.illustration.analysis_session.novel.user.id
#         elif hasattr(instance, 'character_profile') and instance.character_profile:
#             user_id = instance.character_profile.novel.user.id
#         elif hasattr(instance, 'analysis_session') and instance.analysis_session:
#             user_id = instance.analysis_session.novel.user.id
#     except Exception:
#         user_id = "unknown"

#     user_folder = f"user_{user_id}"
#     return os.path.join(user_folder, 'assets', asset_type, filename)

# def user_character_image_path(instance, filename):
#     return get_user_asset_path(instance, filename, 'characters/images')

# def user_character_voice_path(instance, filename):
#     return get_user_asset_path(instance, filename, 'characters/voices')

# def user_illustration_path(instance, filename):
#     return get_user_asset_path(instance, filename, 'illustrations')

# def user_video_path(instance, filename):
#     return get_user_asset_path(instance, filename, 'videos')
    
# class CharacterImage(models.Model):
#     character_profile = models.ForeignKey(CharacterProfileAnalysis, on_delete=models.CASCADE, related_name='characters_image_asset')
#     emotion = models.CharField(max_length=50, help_text="e.g., happy, sad, angry", blank=True)
#     image = models.ImageField(upload_to=user_character_image_path, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         unique_together = ('character_profile', 'emotion')
    
#     def __str__(self):
#         return f"Image for {self.character_profile.name} - {self.emotion}"

# class CharacterVoice(models.Model):
#     sentence = models.OneToOneField(SentenceAnalysis, on_delete=models.CASCADE, related_name='character_voice_asset')
#     voice = models.FileField(upload_to=user_character_voice_path, null=True, blank=True)
#     duration = models.FloatField(help_text="Duration in seconds", default=0.0)
#     created_at = models.DateTimeField(auto_now_add=True)
    
# class IllustrationImage(models.Model):
#     illustration = models.OneToOneField(IllustrationAnalysis, on_delete=models.CASCADE, related_name='image_asset')
#     image = models.ImageField(upload_to=user_illustration_path, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
# class Video(models.Model):
#     analysis_session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='videos_asset')
#     name = models.CharField(max_length=255)
#     version = models.PositiveIntegerField(default=1)
#     video_file = models.FileField(upload_to=user_video_path, null=True, blank=True)
#     duration = models.DurationField(help_text="Format: HH:MM:SS", null=True, blank=True)
#     file_size = models.FloatField(help_text="Size in MB", default=0.0)
#     STATUS_CHOICES = (
#         ('processing', 'Processing'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#     )
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         unique_together = ('analysis_session', 'version')

#     def __str__(self):
#         return f"Video: {self.name} for {self.analysis_session.name}"