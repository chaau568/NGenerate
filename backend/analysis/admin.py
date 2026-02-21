# from django.contrib import admin
# from .models import (
#     AnalysisSession,
#     SentenceAnalysis,
#     IllustrationAnalysis,
#     CharacterProfileAnalysis,
#     ProcessingStep,
# )

# # =========================
# # Inlines
# # =========================

# class SentenceAnalysisInline(admin.TabularInline):
#     model = SentenceAnalysis
#     extra = 0
#     fields = (
#         'sentence_index',
#         'chapter',
#         'type',
#         'character_name',
#         'emotion',
#         'short_sentence',
#     )
#     readonly_fields = fields
#     show_change_link = True

#     def short_sentence(self, obj):
#         return obj.sentence[:80] + "..." if len(obj.sentence) > 80 else obj.sentence

#     short_sentence.short_description = "Sentence"


# class IllustrationAnalysisInline(admin.TabularInline):
#     model = IllustrationAnalysis
#     extra = 0
#     fields = (
#         'chapter',
#         'short_positive_prompt',
#         'short_negative_prompt',
#     )
#     readonly_fields = fields
#     show_change_link = True

#     def short_positive_prompt(self, obj):
#         if not obj.positive_prompt:
#             return "-"
#         return obj.positive_prompt[:60] + "..." if len(obj.positive_prompt) > 60 else obj.positive_prompt

#     def short_negative_prompt(self, obj):
#         if not obj.negative_prompt:
#             return "-"
#         return obj.negative_prompt[:60] + "..." if len(obj.negative_prompt) > 60 else obj.negative_prompt

#     short_positive_prompt.short_description = "Positive Prompt"
#     short_negative_prompt.short_description = "Negative Prompt"


# class ProcessingStepInline(admin.TabularInline):
#     model = ProcessingStep
#     extra = 0
#     fields = (
#         'phase',
#         'name',
#         'order',
#         'status',
#         'is_read',
#         'start_at',
#         'finish_at',
#     )
#     readonly_fields = fields
#     ordering = ('phase', 'order')
    
# class ProcessingStepInline(admin.TabularInline):
#     model = ProcessingStep
#     extra = 0
#     fields = (
#         'phase',
#         'step_name_label',
#         'order',
#         'status',
#         'duration',
#         'is_read',
#         'start_at',
#         'finish_at',
#         'short_error',
#     )
#     readonly_fields = fields
#     ordering = ('phase', 'order')

#     def step_name_label(self, obj):
#         return obj.get_name_display()
#     step_name_label.short_description = "Step"

#     def duration(self, obj):
#         if obj.start_at and obj.finish_at:
#             delta = obj.finish_at - obj.start_at
#             return str(delta).split('.')[0]
#         return "-"
#     duration.short_description = "Duration"

#     def short_error(self, obj):
#         if not obj.error_message:
#             return "-"
#         return obj.error_message[:60] + "..." if len(obj.error_message) > 60 else obj.error_message
#     short_error.short_description = "Error"



# # =========================
# # AnalysisSession Admin
# # =========================

# @admin.register(AnalysisSession)
# class AnalysisSessionAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'name',
#         'novel',
#         'status',
#         'analysis_progress',
#         'generation_progress',
#         'total_credits',
#         'created_at',
#         'finished_at',
#     )
#     list_filter = (
#         'status',
#         'created_at',
#     )
#     search_fields = (
#         'name',
#         'novel__title',
#         'novel__user__username',
#     )
#     readonly_fields = (
#         'analysis_progress',
#         'generation_progress',
#         'total_credits',
#         'created_at',
#         'finished_at',
#     )
#     filter_horizontal = ('chapters',)

#     inlines = [
#         ProcessingStepInline,
#         SentenceAnalysisInline,
#         IllustrationAnalysisInline,
#     ]


# # =========================
# # SentenceAnalysis Admin
# # =========================

# @admin.register(SentenceAnalysis)
# class SentenceAnalysisAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'analysis_session',
#         'chapter',
#         'sentence_index',
#         'type',
#         'character_name',
#         'emotion',
#         'short_sentence',
#     )
#     list_filter = (
#         'type',
#         'emotion',
#         'chapter',
#     )
#     search_fields = (
#         'sentence',
#         'character_name',
#     )

#     def short_sentence(self, obj):
#         return obj.sentence[:80] + "..." if len(obj.sentence) > 80 else obj.sentence

#     short_sentence.short_description = "Sentence"


# # =========================
# # CharacterProfileAnalysis Admin
# # =========================

# @admin.register(CharacterProfileAnalysis)
# class CharacterProfileAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'name',
#         'sex',
#         'age',
#         'race',
#         'novel',
#     )
#     list_filter = (
#         'sex',
#         'race',
#     )
#     search_fields = (
#         'name',
#         'appearance',
#         'base_personality',
#     )


# # =========================
# # IllustrationAnalysis Admin
# # =========================

# @admin.register(IllustrationAnalysis)
# class IllustrationAnalysisAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'analysis_session',
#         'chapter',
#         'short_positive_prompt',
#     )
#     search_fields = (
#         'positive_prompt',
#         'negative_prompt',
#     )

#     def short_positive_prompt(self, obj):
#         if not obj.positive_prompt:
#             return "-"
#         return obj.positive_prompt[:80] + "..." if len(obj.positive_prompt) > 80 else obj.positive_prompt

#     short_positive_prompt.short_description = "Positive Prompt"


# # =========================
# # ProcessingStep Admin
# # =========================

# @admin.register(ProcessingStep)
# class ProcessingStepAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'analysis_session',
#         'phase_label',
#         'step_label',
#         'order',
#         'status',
#         'duration',
#         'is_read',
#         'start_at',
#         'finish_at',
#     )

#     list_filter = (
#         'phase',
#         'status',
#         'is_read',
#     )

#     search_fields = (
#         'analysis_session__name',
#         'analysis_session__novel__title',
#         'error_message',
#     )

#     ordering = ('analysis_session', 'phase', 'order')

#     readonly_fields = (
#         'analysis_session',
#         'phase',
#         'name',
#         'order',
#         'status',
#         'start_at',
#         'finish_at',
#         'duration',
#         'error_message',
#     )

#     fieldsets = (
#         ('Basic Info', {
#             'fields': (
#                 'analysis_session',
#                 'phase',
#                 'name',
#                 'order',
#                 'status',
#             )
#         }),
#         ('Timing', {
#             'fields': (
#                 'start_at',
#                 'finish_at',
#                 'duration',
#             )
#         }),
#         ('Error', {
#             'fields': (
#                 'error_message',
#             )
#         }),
#     )

#     def step_label(self, obj):
#         return obj.get_name_display()
#     step_label.short_description = "Step"

#     def phase_label(self, obj):
#         return obj.get_phase_display()
#     phase_label.short_description = "Phase"

#     def duration(self, obj):
#         if obj.start_at and obj.finish_at:
#             delta = obj.finish_at - obj.start_at
#             return str(delta).split('.')[0]
#         return "-"
#     duration.short_description = "Duration"
