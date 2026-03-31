from django.urls import path
from . import views

urlpatterns = [
    # ── Packages ──────────────────────────────────────────
    path("packages/", views.list_packages, name="list_packages"),
    path("packages/all/", views.list_all_packages, name="list_all_packages"),
    path("packages/create/", views.create_package, name="create_package"),
    path("packages/<int:package_id>/", views.update_package, name="update_package"),
    path("packages/<int:package_id>/delete/", views.delete_package, name="delete_package"),

    # ── Transactions ──────────────────────────────────────
    path("get/<int:transaction_id>/", views.get_payment, name="get_payment"),
    path("create/", views.create_payment, name="create_payment"),
    path("pending/", views.pending_transactions, name="pending_transactions"),
    path("confirm/<int:transaction_id>/", views.confirm_payment, name="confirm_payment"),
    path("check/<int:transaction_id>/", views.check_payment, name="check_payment"),
    path("my-payments/", views.my_payments, name="my_payments"),

    # ── Credit Logs ───────────────────────────────────────
    path("my-credit-logs/", views.my_credit_logs, name="my_credit_logs"),

    # ── Stripe Webhook ─────────────────────────────────────
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("webhook/stripe/verify_session", views.verify_session, name="verify_session"),
]