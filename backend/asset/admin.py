from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CharacterProfileAsset,
    CharacterAsset,
    NarratorVoice,
    IllustrationImage,
    Video,
)

# =====================================================
# BASE MIXIN สำหรับแสดง Preview ไฟล์ต่างๆ
# =====================================================


class FilePreviewMixin:
    file_field_name = None

    def file_preview(self, obj):
        file_field = getattr(obj, self.file_field_name, None)
        if not file_field or not file_field.url:
            return "-"

        url = file_field.url
        # ตรวจสอบนามสกุลไฟล์เพื่อแสดงผลให้ถูกต้อง
        ext = url.lower()

        if ext.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return format_html(
                '<img src="{}" style="height:70px; border: 1px solid #ccc; border-radius:4px;" />',
                url,
            )

        if ext.endswith((".mp3", ".wav", ".ogg")):
            return format_html(
                '<audio controls src="{}" style="height:35px; width:200px;"></audio>',
                url,
            )

        if ext.endswith(".mp4"):
            return format_html(
                '<video src="{}" height="70" style="border-radius:4px;" controls></video>',
                url,
            )

        return format_html('<a href="{}" target="_blank">View File</a>', url)

    file_preview.short_description = "Preview"


# =====================================================
# CHARACTER MASTER IMAGE
# =====================================================


@admin.register(CharacterProfileAsset)
class CharacterProfileAssetAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"

    list_display = (
        "id",
        "file_preview",
        "character_profile",
        "created_at",
    )

    search_fields = (
        "character_profile__name",
        "character_profile__novel__title",
    )

    readonly_fields = ("created_at", "file_preview")


# =====================================================
# CHARACTER EMOTION IMAGE
# =====================================================


@admin.register(CharacterAsset)
class CharacterAssetAdmin(FilePreviewMixin, admin.ModelAdmin):

    file_field_name = "image"

    list_display = (
        "id",
        "file_preview",
        "get_character",
        "get_emotion",
        "session",
        "created_at",
    )

    list_filter = ("session",)

    readonly_fields = ("created_at", "file_preview")

    def get_character(self, obj):
        return obj.character.character_profile.name

    get_character.short_description = "Character"

    def get_emotion(self, obj):
        return obj.character.emotion

    get_emotion.short_description = "Emotion"


# =====================================================
# NARRATION VOICE
# =====================================================


@admin.register(NarratorVoice)
class NarratorVoiceAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "voice"
    list_display = (
        "id",
        "file_preview",
        "get_sentence_idx",
        "duration",
        "session",
        "created_at",
    )
    list_filter = ("session", "created_at")
    search_fields = ("sentence__sentence", "session__id")
    readonly_fields = ("created_at", "file_preview")

    def get_sentence_idx(self, obj):
        return f"Sent {obj.sentence.sentence_index}"

    get_sentence_idx.short_description = "Sentence No."


# =====================================================
# ILLUSTRATION IMAGE (SCENE)
# =====================================================


@admin.register(IllustrationImage)
class IllustrationImageAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"
    list_display = (
        "id",
        "file_preview",
        "get_chapter_order",
        "session",
        "created_at",
    )
    list_filter = ("session", "created_at")
    search_fields = ("illustration__chapter__order", "session__name")
    readonly_fields = ("created_at", "file_preview")

    def get_chapter_order(self, obj):
        return f"Chapter {obj.illustration.chapter.order}"

    get_chapter_order.short_description = "Chapter"


# =====================================================
# VIDEO
# =====================================================


@admin.register(Video)
class VideoAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "video_file"
    list_display = (
        "id",
        "file_preview",
        "session",
        "version",
        "is_final",
        "duration",
        "file_size",
        "created_at",
    )
    list_filter = ("is_final", "session", "created_at")
    search_fields = ("session__name", "session__id")
    readonly_fields = ("created_at", "file_preview", "file_size")

    fieldsets = (
        ("Status", {"fields": ("session", "version", "is_final")}),
        (
            "Media Info",
            {"fields": ("video_file", "file_preview", "duration", "file_size")},
        ),
        ("Timestamps", {"fields": ("created_at",)}),
    )
