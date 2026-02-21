# from django.contrib import admin
# from django.utils.html import format_html
# from .models import (
#     CharacterImage,
#     CharacterVoice,
#     IllustrationImage,
#     Video,
# )

# # ==================================================
# # Helpers
# # ==================================================

# def image_preview(obj):
#     if obj.image:
#         return format_html(
#             '<img src="{}" style="max-height: 150px; border-radius: 6px;" />',
#             obj.image.url
#         )
#     return "-"

# image_preview.short_description = "Preview"


# def audio_player(obj):
#     if obj.voice:
#         return format_html(
#             '<audio controls style="width: 250px;">'
#             '<source src="{}" type="audio/mpeg">'
#             '</audio>',
#             obj.voice.url
#         )
#     return "-"

# audio_player.short_description = "Voice"


# def video_download(obj):
#     if obj.video_file:
#         return format_html(
#             '<a href="{}" target="_blank">Download</a>',
#             obj.video_file.url
#         )
#     return "-"

# video_download.short_description = "Video"


# # ==================================================
# # Character Image Admin
# # ==================================================

# @admin.register(CharacterImage)
# class CharacterImageAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'character_profile',
#         'emotion',
#         'preview',
#         'created_at',
#     )
#     list_filter = (
#         'emotion',
#         'character_profile__novel',
#     )
#     search_fields = (
#         'character_profile__name',
#     )
#     readonly_fields = (
#         'preview',
#         'created_at',
#     )
#     fields = (
#         'character_profile',
#         'emotion',
#         'preview',
#         'image',
#         'created_at',
#     )

#     def preview(self, obj):
#         return image_preview(obj)


# # ==================================================
# # Character Voice Admin
# # ==================================================

# @admin.register(CharacterVoice)
# class CharacterVoiceAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'sentence',
#         'duration',
#         'voice_player',
#         'created_at',
#     )
#     list_filter = (
#         'sentence__analysis_session',
#     )
#     search_fields = (
#         'sentence__sentence',
#         'sentence__character_name',
#     )
#     readonly_fields = (
#         'voice_player',
#         'created_at',
#     )
#     fields = (
#         'sentence',
#         'duration',
#         'voice_player',
#         'voice',
#         'created_at',
#     )

#     def voice_player(self, obj):
#         return audio_player(obj)


# # ==================================================
# # Illustration Image Admin
# # ==================================================

# @admin.register(IllustrationImage)
# class IllustrationImageAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'illustration',
#         'preview',
#         'created_at',
#     )
#     list_filter = (
#         'illustration__analysis_session',
#     )
#     search_fields = (
#         'illustration__positive_prompt',
#         'illustration__negative_prompt',
#     )
#     readonly_fields = (
#         'preview',
#         'created_at',
#     )
#     fields = (
#         'illustration',
#         'preview',
#         'image',
#         'created_at',
#     )

#     def preview(self, obj):
#         return image_preview(obj)


# # ==================================================
# # Video Admin
# # ==================================================

# @admin.register(Video)
# class VideoAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'name',
#         'analysis_session',
#         'version',
#         'status',
#         'duration',
#         'file_size',
#         'video_link',
#         'created_at',
#     )
#     list_filter = (
#         'status',
#         'analysis_session',
#         'created_at',
#     )
#     search_fields = (
#         'name',
#         'analysis_session__name',
#         'analysis_session__novel__title',
#     )
#     readonly_fields = (
#         'video_link',
#         'created_at',
#     )
#     fields = (
#         'analysis_session',
#         'name',
#         'version',
#         'status',
#         'duration',
#         'file_size',
#         'video_link',
#         'video_file',
#         'created_at',
#     )

#     def video_link(self, obj):
#         return video_download(obj)
