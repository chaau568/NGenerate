import os
from django.db import models

from ngenerate_sessions.models import (
    Session,
    GenerationRun,
    CharacterProfile,
    Sentence,
    Illustration,
    SceneCharacter,
)

from utils.runpod_storage import delete_runpod_file


# =====================================================
# STORAGE PATH HELPERS
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


def generation_run_storage_path(generation_run, folder, filename):
    session = generation_run.session
    user_id = session.novel.user_id
    novel_id = session.novel_id
    session_id = session.id
    version = generation_run.version
    return "/".join(
        [
            "user_data",
            f"user_{user_id}",
            f"novel_{novel_id}",
            f"session_{session_id}",
            f"v{version}",
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
    return "/".join(
        [
            "user_data",
            f"user_{user_id}",
            f"novel_{novel_id}",
            "characters",
            f"p{profile_id}",
            f"master{ext}",
        ]
    )


class CharacterProfileAsset(models.Model):
    """Master image ของ character — ใช้ร่วมกันทุก GenerationRun"""

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
# CHARACTER SCENE ASSET
# แทน CharacterAsset เดิมที่ผูกกับ Character (emotion-based)
# ตอนนี้ผูกกับ SceneCharacter (scene-based)
# =====================================================


def character_asset_path(instance, filename):
    """
    path: .../session_X/v{version}/character_scenes/ch{N}_s{N}_p{N}.png
    """
    sc = instance.scene_character
    chapter_order = sc.illustration.chapter.order
    scene_index = sc.illustration.scene_index
    profile_id = sc.character_profile_id
    ext = os.path.splitext(filename)[1] or ".png"
    fname = f"ch{chapter_order}_s{scene_index}_p{profile_id}{ext}"
    return generation_run_storage_path(
        instance.generation_run, "character_scenes", fname
    )


class CharacterAsset(models.Model):
    """Scene character image — แยกตาม GenerationRun, ผูกกับ SceneCharacter"""

    generation_run = models.ForeignKey(
        GenerationRun,
        on_delete=models.CASCADE,
        related_name="character_assets",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="character_assets",
    )
    scene_character = models.ForeignKey(
        SceneCharacter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assets",
    )
    image = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generation_run", "scene_character"],
                condition=models.Q(generation_run__isnull=False),
                name="unique_character_asset_per_run",
            )
        ]

    def __str__(self):
        sc = self.scene_character
        version = f" v{self.generation_run.version}" if self.generation_run else ""
        return (
            f"{sc.character_profile.name} | "
            f"Ch{sc.illustration.chapter.order} "
            f"Scene{sc.illustration.scene_index}{version}"
        )

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
    fname = f"sent_{sentence_index}.{ext}"
    return generation_run_storage_path(instance.generation_run, "voices", fname)


class NarratorVoice(models.Model):

    generation_run = models.ForeignKey(
        GenerationRun,
        on_delete=models.CASCADE,
        related_name="voices",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="voices",
    )
    sentence = models.ForeignKey(
        Sentence,
        on_delete=models.CASCADE,
        related_name="voice_assets",
    )
    voice = models.CharField(max_length=500)
    duration = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generation_run", "sentence"],
                condition=models.Q(generation_run__isnull=False),
                name="unique_narrator_voice_per_run",
            )
        ]

    def __str__(self):
        version = f" v{self.generation_run.version}" if self.generation_run else ""
        return f"Voice | Sent {self.sentence.sentence_index}{version}"

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
    scene_index = instance.illustration.scene_index
    ext = filename.split(".")[-1] if "." in filename else "png"
    fname = f"scene_ch{chapter_order}_s{scene_index}.{ext}"
    return generation_run_storage_path(instance.generation_run, "scenes", fname)


class IllustrationImage(models.Model):

    generation_run = models.ForeignKey(
        GenerationRun,
        on_delete=models.CASCADE,
        related_name="scene_images",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="scene_images",
    )
    illustration = models.ForeignKey(
        Illustration,
        on_delete=models.CASCADE,
        related_name="image_assets",
    )
    image = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generation_run", "illustration"],
                condition=models.Q(generation_run__isnull=False),
                name="unique_illustration_image_per_run",
            )
        ]

    def __str__(self):
        version = f" v{self.generation_run.version}" if self.generation_run else ""
        return f"Scene | Ch {self.illustration.chapter.order}{version}"

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
    fname = f"video_v{instance.generation_run.version}.mp4"
    return generation_run_storage_path(instance.generation_run, "videos", fname)


class Video(models.Model):

    generation_run = models.OneToOneField(
        GenerationRun,
        on_delete=models.CASCADE,
        related_name="video",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="videos",
    )

    @property
    def version(self):
        return self.generation_run.version

    video_path = models.CharField(max_length=500, blank=True, null=True)
    duration = models.FloatField(default=0.0)
    file_size = models.FloatField(default=0.0)
    is_final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        version = f" v{self.version}" if self.generation_run else ""
        return f"Video{version} | Session {self.session.id}"

    def delete(self, *args, **kwargs):
        if self.video_path:
            try:
                delete_runpod_file(self.video_path)
            except Exception:
                pass
        super().delete(*args, **kwargs)
