from django.contrib import admin
from .models import (
    Session, CharacterProfile, Sentence, 
    Illustration, ProcessingStep
)

class ProcessingStepInline(admin.TabularInline):
    model = ProcessingStep
    extra = 0
    readonly_fields = ('start_at', 'finish_at')
    ordering = ('phase', 'order')

class SentenceInline(admin.TabularInline):
    model = Sentence
    extra = 0
    fields = ('chapter', 'character', 'type', 'sentence')
    readonly_fields = ('chapter', 'sentence_index', 'get_character_name')
    
    def get_character_name(self, obj):
        return obj.character.name if obj.character else "-"

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'novel', 'status', 'session_type', 'is_analysis_done', 'is_generation_done', 'created_at')
    list_filter = ('status', 'session_type', 'is_analysis_done', 'is_generation_done')
    search_fields = ('name', 'novel__title', 'novel__user__email')
    
    # ล็อกค่าใช้จ่ายและสถานะสำคัญไม่ให้ Admin แก้ไขมือบอน
    readonly_fields = (
        'analyze_credits', 'generate_credits', 'locked_credits',
        'created_at', 'analysis_finished_at', 'generation_finished_at'
    )
    
    filter_horizontal = ('chapters',) # ทำให้เลือก Chapter ในหน้า Session ได้ง่ายขึ้น
    inlines = [ProcessingStepInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('novel', 'name', 'status', 'session_type', 'chapters')
        }),
        ('Credit & Billing', {
            'fields': ('analyze_credits', 'generate_credits', 'locked_credits')
        }),
        ('Progress Flags', {
            'fields': (
                'is_analysis_done', 'is_generation_done', 
                'analysis_finished_at', 'generation_finished_at', 'created_at'
            )
        }),
    )

@admin.register(CharacterProfile)
class CharacterProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'novel', 'sex', 'age', 'race', 'updated_at')
    list_filter = ('race', 'sex')
    search_fields = ('name', 'novel__title')
    readonly_fields = ('updated_at',)

@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = (
        'session',
        'chapter',
        'sentence_index',
        'get_character_name',
        'type'
    )
    list_filter = ('type', 'session')
    search_fields = ('sentence', 'character__name')

    def get_character_name(self, obj):
        return obj.character.name if obj.character else "-"

    get_character_name.short_description = "Character"

@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'chapter')
    search_fields = ('session__name', 'positive_prompt')

@admin.register(ProcessingStep)
class ProcessingStepAdmin(admin.ModelAdmin):
    list_display = ('session', 'phase', 'name', 'order', 'status', 'start_at', 'finish_at')
    list_filter = ('phase', 'status')
    # readonly_fields = ('start_at', 'finish_at')