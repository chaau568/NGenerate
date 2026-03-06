from django.contrib import admin
from .models import (
    Session,
    CharacterProfile,
    Sentence,
    SentenceCharacter,
    Character,
    Illustration,
    ProcessingStep,
)

# =========================================================
# Inlines
# =========================================================


class ProcessingStepInline(admin.TabularInline):
    model = ProcessingStep
    extra = 0
    readonly_fields = ("start_at", "finish_at")
    ordering = ("phase", "order")


class SentenceCharacterInline(admin.TabularInline):
    model = SentenceCharacter
    extra = 0
    autocomplete_fields = ["character"]


# =========================================================
# Session Admin
# =========================================================


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
        "is_generation_done",
        "created_at",
    )

    list_filter = (
        "status",
        "session_type",
        "style",
        "is_analysis_done",
        "is_generation_done",
    )

    search_fields = (
        "name",
        "novel__title",
        "novel__user__email",
    )

    readonly_fields = (
        "analyze_credits",
        "generate_credits",
        "locked_credits",
        "created_at",
        "analysis_finished_at",
        "generation_finished_at",
    )

    filter_horizontal = ("chapters",)

    inlines = [ProcessingStepInline]

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
                    "generate_credits",
                    "locked_credits",
                )
            },
        ),
        (
            "Progress Flags",
            {
                "fields": (
                    "is_analysis_done",
                    "is_generation_done",
                    "analysis_finished_at",
                    "generation_finished_at",
                    "created_at",
                )
            },
        ),
    )


# =========================================================
# Character Profile Admin
# =========================================================


@admin.register(CharacterProfile)
class CharacterProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "novel",
        "sex",
        "age",
        "race",
        "updated_at",
    )

    list_filter = ("sex", "race")
    search_fields = ("name", "novel__title")
    readonly_fields = ("updated_at",)


# =========================================================
# Character Admin
# =========================================================


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):

    list_display = (
        "session",
        "chapter",
        "character_profile",
        "emotion",
    )

    list_filter = (
        "session",
        "emotion",
    )

    search_fields = (
        "character_profile__name",
        "positive_prompt",
    )


# =========================================================
# Sentence Admin
# =========================================================


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = (
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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("session", "chapter")
            .prefetch_related("sentence_characters__character__character_profile")
        )

    def get_characters(self, obj):
        chars = obj.sentence_characters.all()

        return (
            ", ".join(c.character.character_profile.name for c in chars)
            if chars
            else "-"
        )

    get_characters.short_description = "Characters in Scene"

    def short_sentence(self, obj):
        return obj.sentence[:50] + "..." if len(obj.sentence) > 50 else obj.sentence

    short_sentence.short_description = "Sentence Text"


# =========================================================
# Illustration Admin
# =========================================================


@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "chapter")
    list_filter = ("session",)
    search_fields = ("session__name", "positive_prompt")


# =========================================================
# Processing Step Admin
# =========================================================


@admin.register(ProcessingStep)
class ProcessingStepAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "phase",
        "name",
        "order",
        "status",
        "start_at",
        "finish_at",
    )

    list_filter = ("phase", "status", "session")
