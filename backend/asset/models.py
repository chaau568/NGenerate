import os
from django.db import models
from ngenerate_sessions.models import Session, Character, Illustration, Sentence


# =====================================================
# STORAGE PATH
# =====================================================

def get_session_asset_path(instance, filename, asset_folder):
    """
    ngenerate_storage/user_{user_id}/session_{session_id}/asset_folder/filename
    """
    user_id = instance.session.novel.user.id 
    session_id = instance.session.id

    return os.path.join(
        "ngenerate_storage",
        f"user_{user_id}",
        f"session_{session_id}",
        asset_folder,
        filename
    )


def character_image_path(instance, filename):
    return get_session_asset_path(instance, filename, "character_image")


def character_voice_path(instance, filename):
    return get_session_asset_path(instance, filename, "character_voice")


def illustration_image_path(instance, filename):
    return get_session_asset_path(instance, filename, "scene_image")


def video_path(instance, filename):
    return get_session_asset_path(instance, filename, "videos")


# =====================================================
# MODELS
# =====================================================

class CharacterImage(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="character_images"
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="image_assets"
    )

    image = models.ImageField(upload_to=character_image_path)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "character"],
                name="unique_character_image_per_session"
            )
        ]

    def __str__(self):
        return f"CharacterImage - {self.character.name} (Session {self.session.id})"

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)


class CharacterVoice(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="character_voices"
    )

    sentence = models.OneToOneField(
        Sentence,
        on_delete=models.CASCADE,
        related_name="voice_asset"
    )

    voice = models.FileField(upload_to=character_voice_path)
    duration = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"{self.session} | {self.sentence}"
    
    def delete(self, *args, **kwargs):
        self.voice.delete(save=False)
        super().delete(*args, **kwargs)


class IllustrationImage(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="scene_images"
    )

    illustration = models.OneToOneField(
        Illustration,
        on_delete=models.CASCADE,
        related_name="image_asset"
    )

    image = models.ImageField(upload_to=illustration_image_path)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]
        
    def __str__(self):
        return f"{self.session} | {self.illustration}"

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)


class Video(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="videos"
    )

    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)

    video_file = models.FileField(upload_to=video_path)
    duration = models.DurationField(null=True, blank=True)
    file_size = models.FloatField(default=0.0)

    is_final = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "version"],
                name="unique_video_version_per_session"
            )
        ]

    def __str__(self):
        return f"Video v{self.version} - Session {self.session.id}"

    def delete(self, *args, **kwargs):
        self.video_file.delete(save=False)
        super().delete(*args, **kwargs)