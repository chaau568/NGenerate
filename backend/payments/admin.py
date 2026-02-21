from django.contrib import admin
from .models import Package, Transaction, CreditLog


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "credits_limit",
        "duration_days",
        "is_active",
        "create_at",
    )

    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("create_at", "update_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "package",
        "amount",
        "credit_amount",
        "payment_status",
        "payment_ref",
        "created_at",
    )

    list_filter = ("payment_status", "created_at")
    search_fields = ("user__email", "payment_ref")
    readonly_fields = (
        "created_at",
        "updated_at",
        "start_at",
        "expire_at",
    )

    actions = ["mark_as_success"]

    def mark_as_success(self, request, queryset):
        updated = queryset.update(payment_status="success")
        self.message_user(request, f"{updated} transactions marked as success.")

    mark_as_success.short_description = "Mark selected transactions as SUCCESS"


@admin.register(CreditLog)
class CreditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "amount",
        "transaction",
        "created_at",
    )

    list_filter = ("type", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)