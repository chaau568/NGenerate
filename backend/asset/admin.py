from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CharacterImage,
    CharacterVoice,
    IllustrationImage,
    Video,
)


# =====================================================
# BASE MIXIN
# =====================================================

class FilePreviewMixin:
    """
    ใช้สำหรับแสดง preview / download link ของไฟล์
    """

    def file_preview(self, obj):
        if not obj:
            return "-"
        file_field = getattr(obj, self.file_field_name, None)
        if not file_field:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">Open file</a>',
            file_field.url
        )

    file_preview.short_description = "File Preview"


# =====================================================
# CHARACTER IMAGE
# =====================================================

@admin.register(CharacterImage)
class CharacterImageAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"

    list_display = (
        "id",
        "session",
        "character",
        "file_preview",
        "created_at",
    )

    list_filter = (
        "session",
        "character",
        "created_at",
    )

    search_fields = (
        "character__name",
        "session__id",
    )

    readonly_fields = (
        "created_at",
        "file_preview",
    )

    ordering = ("-created_at",)


# =====================================================
# CHARACTER VOICE
# =====================================================

@admin.register(CharacterVoice)
class CharacterVoiceAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "voice"

    list_display = (
        "id",
        "session",
        "sentence",
        "duration",
        "file_preview",
        "created_at",
    )

    list_filter = (
        "session",
        "created_at",
    )

    search_fields = (
        "sentence__text",
        "session__id",
    )

    readonly_fields = (
        "created_at",
        "file_preview",
    )

    ordering = ("-created_at",)


# =====================================================
# ILLUSTRATION IMAGE
# =====================================================

@admin.register(IllustrationImage)
class IllustrationImageAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"

    list_display = (
        "id",
        "session",
        "illustration",
        "file_preview",
        "created_at",
    )

    list_filter = (
        "session",
        "created_at",
    )

    search_fields = (
        "illustration__id",
        "session__id",
    )

    readonly_fields = (
        "created_at",
        "file_preview",
    )

    ordering = ("-created_at",)


# =====================================================
# VIDEO
# =====================================================

@admin.register(Video)
class VideoAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "video_file"

    list_display = (
        "id",
        "session",
        "name",
        "version",
        "is_final",
        "duration",
        "file_size",
        "file_preview",
        "created_at",
    )

    list_filter = (
        "session",
        "is_final",
        "created_at",
    )

    search_fields = (
        "name",
        "session__id",
    )

    readonly_fields = (
        "created_at",
        "file_preview",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (None, {
            "fields": (
                "session",
                "name",
                "version",
                "is_final",
            )
        }),
        ("Video Info", {
            "fields": (
                "video_file",
                "duration",
                "file_size",
                "file_preview",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at",)
        }),
    )