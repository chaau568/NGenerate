from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import User, UserCredit


class MyUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "role", "status", "is_staff", "is_active")


class UserCreditInline(admin.StackedInline):
    model = UserCredit
    can_delete = False
    extra = 0
    fields = ("available", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = MyUserCreationForm  
    form = UserChangeForm
    model = User

    list_display = (
        "id",
        "email",
        "username",
        "role",
        "status",
        "is_staff",
        "is_active",
        "created_at",
    )

    list_filter = ("role", "status", "is_staff", "is_active")
    search_fields = ("email", "username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login")

    inlines = [UserCreditInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("username",)}),
        ("Business Info", {"fields": ("role", "status")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1", 
                    "password2",
                    "role",
                    "status",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
