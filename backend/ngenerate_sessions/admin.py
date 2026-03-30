from django.contrib import admin
from .models import (
    Session,
    GenerationRun,
    CharacterProfile,
    Sentence,
    Illustration,
    SceneCharacter,
    ProcessingStep,
    GenerationProcessingStep,
)

# --- Inlines ---


class ProcessingStepInline(admin.TabularInline):
    model = ProcessingStep
    extra = 0
    readonly_fields = ("start_at", "finish_at")
    ordering = ("order",)


class GenerationRunInline(admin.TabularInline):
    model = GenerationRun
    extra = 0
    readonly_fields = (
        "version",
        "status",
        "generate_credits",
        "locked_credits",
        "generation_finished_at",
        "created_at",
    )
    fields = (
        "version",
        "style",
        "narrator_voice",
        "status",
        "generate_credits",
        "locked_credits",
        "generation_finished_at",
    )
    ordering = ("-version",)
    show_change_link = True


class SceneCharacterInline(admin.TabularInline):
    """Inline สำหรับแสดงตัวละครที่อยู่ในฉากนั้นๆ (Illustration)"""

    model = SceneCharacter
    extra = 0
    autocomplete_fields = ["character_profile", "session"]


class GenerationProcessingStepInline(admin.TabularInline):
    model = GenerationProcessingStep
    extra = 0
    readonly_fields = ("start_at", "finish_at")
    ordering = ("order",)


# --- Admins ---


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "novel",
        "status",
        "session_type",
        "style",
        "is_analysis_done",
        "created_at",
    )
    list_filter = (
        "status",
        "session_type",
        "style",
        "is_analysis_done",
    )
    search_fields = ("name", "novel__title", "novel__user__email")
    readonly_fields = (
        "analyze_credits",
        "locked_credits",
        "created_at",
        "analysis_finished_at",
    )
    filter_horizontal = ("chapters",)
    inlines = [ProcessingStepInline, GenerationRunInline]
    autocomplete_fields = ["novel"]


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "version",
        "style",
        "status",
        "generate_credits",
        "created_at",
    )
    list_filter = ("status", "style")
    search_fields = ("session__name", "session__novel__title")
    readonly_fields = (
        "version",
        "generate_credits",
        "locked_credits",
        "generation_finished_at",
        "created_at",
    )
    inlines = [GenerationProcessingStepInline]
    autocomplete_fields = ["session"]


@admin.register(CharacterProfile)
class CharacterProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "novel", "sex", "age", "race", "updated_at")
    list_filter = ("sex", "race")
    search_fields = ("name", "novel__title")
    readonly_fields = ("updated_at",)
    ordering = ["name"]


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "chapter",
        "sentence_index",
        "short_sentence",
    )
    list_filter = ("session", "chapter")
    search_fields = ("sentence", "tts_text")
    autocomplete_fields = ["session", "chapter"]

    @admin.display(description="Sentence Text")
    def short_sentence(self, obj):
        return obj.sentence[:50] + "..." if len(obj.sentence) > 50 else obj.sentence


@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "chapter",
        "scene_index",
        "sentence_start",
        "sentence_end",
        "short_description",
    )
    list_filter = ("session", "chapter")
    search_fields = ("scene_description", "positive_prompt")
    autocomplete_fields = ["session", "chapter"]
    inlines = [SceneCharacterInline]

    @admin.display(description="Description")
    def short_description(self, obj):
        return obj.scene_description[:40] + "..." if obj.scene_description else "-"


@admin.register(SceneCharacter)
class SceneCharacterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "get_illustration_info",
        "character_profile",
        "action",
        "expression",
    )
    list_filter = ("session",)
    search_fields = ("character_profile__name", "action", "expression")
    autocomplete_fields = ["session", "illustration", "character_profile"]

    @admin.display(description="Illustration (Ch | Scene)")
    def get_illustration_info(self, obj):
        return (
            f"Ch{obj.illustration.chapter.order} | Scene {obj.illustration.scene_index}"
        )


@admin.register(ProcessingStep)
class ProcessingStepAdmin(admin.ModelAdmin):
    list_display = ("session", "name", "order", "status", "start_at", "finish_at")
    list_filter = ("status", "session")
    search_fields = ("name", "session__name")


@admin.register(GenerationProcessingStep)
class GenerationProcessingStepAdmin(admin.ModelAdmin):
    list_display = (
        "generation_run",
        "name",
        "order",
        "status",
        "start_at",
        "finish_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "generation_run__session__name")
