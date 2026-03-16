from django.contrib import admin, messages
from django.utils.html import format_html
from django.db import transaction
from .models import Package, Transaction, CreditLog
from payments.services.payment_service import PaymentService

# =====================================================
# PACKAGE ADMIN
# =====================================================


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "credits",
        "is_active",
        "recommendation",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


# =====================================================
# TRANSACTION ADMIN (เพิ่มระบบเติมเครดิตอัตโนมัติ)
# =====================================================


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "package",
        "amount",
        "credit_amount",
        "colored_status",
        "payment_ref",
        "expire_at",
        "created_at",
    )

    list_filter = ("payment_status", "created_at")
    search_fields = ("user__email", "payment_ref")
    readonly_fields = ("created_at", "updated_at")

    actions = ["mark_as_success_and_add_credit"]

    @admin.display(description="Status")
    def colored_status(self, obj):
        colors = {
            "success": "#28a745",
            "pending": "#ffc107",
            "failed": "#dc3545",
            "expired": "#6c757d",
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.payment_status, "#000"),
            obj.get_payment_status_display(),
        )

    @admin.action(description="Mark selected as SUCCESS (Add Credit)")
    def mark_as_success_and_add_credit(self, request, queryset):
        success_count = 0
        error_count = 0

        for tx in queryset:
            if tx.payment_status == "pending":
                try:
                    with transaction.atomic():
                        PaymentService.mark_success(tx.id)
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request,
                        f"Error processing ID {tx.id}: {str(e)}",
                        messages.ERROR,
                    )
            else:
                error_count += 1

        if success_count > 0:
            self.message_user(
                request,
                f"Successfully processed {success_count} transactions and added credits.",
            )

        if error_count > 0:
            self.message_user(
                request,
                f"{error_count} transactions were skipped (already processed or error).",
                messages.WARNING,
            )


# =====================================================
# CREDIT LOG ADMIN
# =====================================================


@admin.register(CreditLog)
class CreditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "colored_amount",
        "transaction",
        "session",
        "created_at",
    )

    list_filter = ("type", "created_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at",)

    @admin.display(description="Amount")
    def colored_amount(self, obj):
        is_positive = obj.type in [
            "topup",
            "refund",
            "analysis_complete",
            "generation_complete",
        ]
        color = "#28a745" if is_positive else "#dc3545"
        prefix = "+" if is_positive else ""
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{:.2f}</span>',
            color,
            prefix,
            obj.amount,
        )
