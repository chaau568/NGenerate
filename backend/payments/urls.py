"""
payments/urls.py
================

สำคัญ: webhook ต้องใช้ Django view ธรรมดา (ไม่ใช่ DRF api_view)
เพราะต้องการ access raw request.body ก่อน parse
และต้องปิด CSRF ด้วย @csrf_exempt
"""
from django.urls import path
from . import views

urlpatterns = [
    # ── Packages ──────────────────────────────────────────
    path("packages/", views.list_packages, name="list_packages"),
    path("packages/all/", views.list_all_packages, name="list_all_packages"),
    path("packages/create/", views.create_package, name="create_package"),

    # ── Transactions ──────────────────────────────────────
    path("create/", views.create_payment, name="create_payment"),
    path("pending/", views.pending_transactions, name="pending_transactions"),
    path("confirm/<int:transaction_id>/", views.confirm_payment, name="confirm_payment"),
    path("check/<int:transaction_id>/", views.check_payment, name="check_payment"),
    path("my-payments/", views.my_payments, name="my_payments"),

    # ── Credit Logs ───────────────────────────────────────
    path("my-credit-logs/", views.my_credit_logs, name="my_credit_logs"),

    # ── Omise Webhook ─────────────────────────────────────
    path("webhook/omise/", views.omise_webhook, name="omise_webhook"),
]