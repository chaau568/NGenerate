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
    # ต้องมี search_fields ใน CharacterAdmin ถึงจะใช้ autocomplete ได้
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
    search_fields = ("name", "novel__title", "novel__user__email")

    # ย้ายฟิลด์คำนวณและฟิลด์เวลามาไว้ใน readonly
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

    # เพิ่ม autocomplete สำหรับ novel เพื่อป้องกัน dropdown ค้างถ้าข้อมูลเยอะ
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
            {"fields": ("analyze_credits", "generate_credits", "locked_credits")},
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
    list_display = ("name", "novel", "sex", "age", "race", "updated_at")
    list_filter = ("sex", "race")
    search_fields = ("name", "novel__title")
    readonly_fields = ("updated_at",)
    # จำเป็นสำหรับการทำ autocomplete ในหน้าอื่นๆ
    ordering = ["name"]


# =========================================================
# Character Admin
# =========================================================


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("session", "chapter", "character_profile", "emotion")
    list_filter = ("emotion", "session")
    # สำคัญ: ต้องเพิ่ม search_fields เพื่อให้ SentenceCharacterInline ใช้งาน autocomplete ได้
    search_fields = ("character_profile__name", "emotion")
    autocomplete_fields = ["session", "chapter", "character_profile"]


# =========================================================
# Sentence Admin
# =========================================================


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


# =========================================================
# Illustration & Processing Step
# =========================================================


@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "chapter")
    search_fields = ("session__name", "positive_prompt")
    autocomplete_fields = ["session", "chapter"]


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
    search_fields = ("name", "session__name")
