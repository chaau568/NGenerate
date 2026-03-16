import os
from django.db import models
from django.conf import settings

from ngenerate_sessions.models import (
    Session,
    CharacterProfile,
    Sentence,
    Illustration,
    Character,
)

from utils.runpod_storage import delete_runpod_file


# =====================================================
# STORAGE BASE
# =====================================================


def session_storage_path(session, folder, filename):

    user_id = session.novel.user_id
    novel_id = session.novel_id
    session_id = session.id

    return "/".join(
        [
            "user_data",
            f"user_{user_id}",
            f"novel_{novel_id}",
            f"session_{session_id}",
            folder,
            filename,
        ]
    )


# =====================================================
# CHARACTER PROFILE ASSET (MASTER IMAGE)
# =====================================================


def character_profile_asset_path(instance, filename):

    user_id = instance.character_profile.novel.user_id
    novel_id = instance.character_profile.novel_id
    profile_id = instance.character_profile.id

    ext = os.path.splitext(filename)[1] or ".png"
    filename = f"master{ext}"

    return "/".join(
        [
            "user_data",
            f"user_{user_id}",
            f"novel_{novel_id}",
            "characters",
            f"p{profile_id}",
            filename,
        ]
    )


class CharacterProfileAsset(models.Model):

    character_profile = models.OneToOneField(
        CharacterProfile,
        on_delete=models.CASCADE,
        related_name="asset",
    )

    image = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Character Master | {self.character_profile.name}"

    def save(self, *args, **kwargs):

        # default avatar
        if not self.image:
            self.image = "assets/defaults/default_avatar.jpg"

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        if self.image and not self.image.startswith("assets/"):
            try:
                delete_runpod_file(self.image)
            except Exception:
                pass

        super().delete(*args, **kwargs)


# =====================================================
# CHARACTER EMOTION IMAGE
# =====================================================


def character_asset_path(instance, filename):

    chapter_order = instance.character.chapter.order
    emotion = instance.character.emotion or "neutral"

    profile_id = instance.character.character_profile_id

    ext = os.path.splitext(filename)[1] or ".png"

    filename = f"ch{chapter_order}_p{profile_id}_{emotion}{ext}"

    return session_storage_path(
        instance.session,
        "character_emotions",
        filename,
    )


class CharacterAsset(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="character_assets",
    )

    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE,
        related_name="asset",
    )

    image = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):

        char = self.character.character_profile.name
        emotion = self.character.emotion

        return f"{char} ({emotion})"

    def delete(self, *args, **kwargs):

        if self.image:
            try:
                delete_runpod_file(self.image)
            except Exception:
                pass

        super().delete(*args, **kwargs)


# =====================================================
# NARRATOR VOICE
# =====================================================


def narrator_voice_path(instance, filename):

    sentence_index = instance.sentence.sentence_index
    ext = filename.split(".")[-1] if "." in filename else "wav"

    filename = f"sent_{sentence_index}.{ext}"

    return session_storage_path(
        instance.session,
        "voices",
        filename,
    )


class NarratorVoice(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="voices",
    )

    sentence = models.OneToOneField(
        Sentence,
        on_delete=models.CASCADE,
        related_name="voice_asset",
    )

    voice = models.CharField(max_length=500)

    duration = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"Voice | Sent {self.sentence.sentence_index}"

    def delete(self, *args, **kwargs):

        if self.voice:
            try:
                delete_runpod_file(self.voice)
            except Exception:
                pass

        super().delete(*args, **kwargs)


# =====================================================
# ILLUSTRATION IMAGE (SCENE)
# =====================================================


def illustration_image_path(instance, filename):

    chapter_order = instance.illustration.chapter.order

    ext = filename.split(".")[-1] if "." in filename else "png"

    filename = f"scene_ch_{chapter_order}.{ext}"

    return session_storage_path(
        instance.session,
        "scenes",
        filename,
    )


class IllustrationImage(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="scene_images",
    )

    illustration = models.OneToOneField(
        Illustration,
        on_delete=models.CASCADE,
        related_name="image_asset",
    )

    image = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"Scene | Ch {self.illustration.chapter.order}"

    def delete(self, *args, **kwargs):

        if self.image:
            try:
                delete_runpod_file(self.image)
            except Exception:
                pass

        super().delete(*args, **kwargs)


# =====================================================
# VIDEO
# =====================================================


def video_path(instance, filename):

    filename = f"video_v{instance.version}.mp4"

    return session_storage_path(
        instance.session,
        "videos",
        filename,
    )


class Video(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="videos",
    )

    version = models.PositiveIntegerField(default=1)

    video_path = models.CharField(max_length=500, blank=True, null=True)

    duration = models.FloatField(default=0.0)

    file_size = models.FloatField(default=0.0)

    is_final = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "version"],
                name="unique_video_version_per_session",
            )
        ]

    def __str__(self):
        return f"Video v{self.version} | Session {self.session.id}"

    def delete(self, *args, **kwargs):

        if self.video_path:
            try:
                delete_runpod_file(self.video_path)
            except Exception:
                pass

        super().delete(*args, **kwargs)
