from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "task_type",
        "status",
        "effective_status_display",
        "is_read",
        "created_at",
    )
    list_filter = ("status", "task_type", "is_read", "created_at")

    search_fields = ("user__username", "user__email", "task_type", "message")

    readonly_fields = ("created_at", "updated_at", "effective_status_display")

    fieldsets = (
        (
            "User & Task",
            {
                "fields": (
                    "user",
                    "task_type",
                    "status",
                    "effective_status_display",
                    "is_read",
                )
            },
        ),
        (
            "Relate To",
            {
                "description": "Notification must relate to either a Session or a Novel.",
                "fields": ("session", "novel"),
            },
        ),
        ("Details", {"fields": ("message", "created_at", "updated_at")}),
    )

    @admin.display(description="Effective Status")
    def effective_status_display(self, obj):
        return obj.get_effective_status()
