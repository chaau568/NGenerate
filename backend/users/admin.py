from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = (
        "id",
        "email",
        "username",
        "role",
        "status",
        "is_staff",
        "is_active",
        "create_at",
    )

    list_filter = (
        "role",
        "status",
        "is_staff",
        "is_active",
    )

    search_fields = ("email", "username")
    ordering = ("-create_at",)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Additional Info", {
            "fields": ('role', 'status')
        }),
    )