from django.contrib import admin
from .models import (
    Session,
    GenerationRun,
    CharacterProfile,
    Sentence,
    SentenceCharacter,
    Character,
    Illustration,
    ProcessingStep,
    GenerationProcessingStep,
)


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


class SentenceCharacterInline(admin.TabularInline):
    model = SentenceCharacter
    extra = 0
    autocomplete_fields = ["character"]


class GenerationProcessingStepInline(admin.TabularInline):
    model = GenerationProcessingStep
    extra = 0
    readonly_fields = ("start_at", "finish_at")
    ordering = ("order",)


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

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "novel",
                    "name",
                    "status",
                    "session_type",
                    "style",
                    "narrator_voice",
                    "chapters",
                )
            },
        ),
        (
            "Credit & Billing",
            {
                "fields": (
                    "analyze_credits",
                    "locked_credits",
                )
            },
        ),
        (
            "Progress Flags",
            {
                "fields": (
                    "is_analysis_done",
                    "analysis_finished_at",
                    "created_at",
                )
            },
        ),
    )


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "version",
        "style",
        "narrator_voice",
        "status",
        "generate_credits",
        "generation_finished_at",
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


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "get_chapter",
        "get_scene_index",
        "character_profile",
        "emotion",
    )
    list_filter = ("emotion", "session")
    search_fields = ("character_profile__name", "emotion")
    autocomplete_fields = ["session", "illustration", "character_profile"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("session", "illustration__chapter", "character_profile")
        )

    @admin.display(description="Chapter", ordering="illustration__chapter__order")
    def get_chapter(self, obj):
        return f"Ch {obj.illustration.chapter.order}"

    @admin.display(description="Scene", ordering="illustration__scene_index")
    def get_scene_index(self, obj):
        return obj.illustration.scene_index


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "chapter",
        "sentence_index",
        "emotion",
        "get_characters",
        "short_sentence",
    )
    list_filter = ("emotion", "session", "chapter")
    search_fields = (
        "sentence",
        "sentence_characters__character__character_profile__name",
    )
    inlines = [SentenceCharacterInline]
    autocomplete_fields = ["session", "chapter"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("session", "chapter")
            .prefetch_related("sentence_characters__character__character_profile")
        )

    @admin.display(description="Characters in Scene")
    def get_characters(self, obj):
        chars = obj.sentence_characters.all()
        return (
            ", ".join(c.character.character_profile.name for c in chars)
            if chars
            else "-"
        )

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
        "scene_description",
    )
    list_filter = ("session", "chapter")
    search_fields = ("session__name", "scene_description", "positive_prompt")
    autocomplete_fields = ["session", "chapter"]
    readonly_fields = ("sentence_start", "sentence_end")


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
