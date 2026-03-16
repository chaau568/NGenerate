from django.contrib import admin
from django.utils.html import format_html
from utils.file_url import build_file_url  # นำเข้าฟังก์ชันจัดการ URL ของคุณ
from .models import (
    CharacterProfileAsset,
    CharacterAsset,
    NarratorVoice,
    IllustrationImage,
    Video,
)

# =====================================================
# BASE MIXIN แก้ไขให้รองรับ CharField (URL String)
# =====================================================


class FilePreviewMixin:
    file_field_name = None

    @admin.display(description="Preview")
    def file_preview(self, obj):
        # ดึงค่า String URL จาก CharField
        raw_path = getattr(obj, self.file_field_name, None)
        if not raw_path:
            return "-"

        # ใช้ build_file_url เพื่อแปลง Path เป็น Full URL (HTTP...)
        url = build_file_url(raw_path)
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


# =====================================================
# ADMIN CLASSES (แก้ไขจุดที่อ้างชื่อฟิลด์ผิด)
# =====================================================


@admin.register(CharacterProfileAsset)
class CharacterProfileAssetAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"
    list_display = ("id", "file_preview", "character_profile", "created_at")
    search_fields = ("character_profile__name", "character_profile__novel__title")
    readonly_fields = ("created_at", "file_preview")


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

    @admin.display(description="Character")
    def get_character(self, obj):
        return obj.character.character_profile.name

    @admin.display(description="Emotion")
    def get_emotion(self, obj):
        return obj.character.emotion


@admin.register(NarratorVoice)
class NarratorVoiceAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "voice"  # ตรงกับ Model
    list_display = (
        "id",
        "file_preview",
        "get_sentence_idx",
        "duration",
        "session",
        "created_at",
    )
    readonly_fields = ("created_at", "file_preview")

    @admin.display(description="Sentence No.")
    def get_sentence_idx(self, obj):
        return f"Sent {obj.sentence.sentence_index}"


@admin.register(IllustrationImage)
class IllustrationImageAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "image"  # ตรงกับ Model
    list_display = ("id", "file_preview", "get_chapter_order", "session", "created_at")
    readonly_fields = ("created_at", "file_preview")

    @admin.display(description="Chapter")
    def get_chapter_order(self, obj):
        return f"Chapter {obj.illustration.chapter.order}"


@admin.register(Video)
class VideoAdmin(FilePreviewMixin, admin.ModelAdmin):
    file_field_name = "video_path"

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
    readonly_fields = ("created_at", "file_preview", "file_size")

    fieldsets = (
        ("Status", {"fields": ("session", "version", "is_final")}),
        (
            "Media Info",
            {"fields": ("video_path", "file_preview", "duration", "file_size")},
        ),
        ("Timestamps", {"fields": ("created_at",)}),
    )
