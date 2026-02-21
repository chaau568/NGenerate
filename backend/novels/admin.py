from django.contrib import admin
from .models import Novel, Chapter


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    ordering = ("order",)


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user",
        "get_total_chapters",
        "get_total_analyzed_chapters",
        "created_at",
    )

    list_filter = ("created_at", "user")
    search_fields = ("title", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ChapterInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "novel",
        "order",
        "is_analyzed",
        "created_at",
    )

    list_filter = ("is_analyzed", "novel")
    search_fields = ("title", "novel__title")
    ordering = ("novel", "order")