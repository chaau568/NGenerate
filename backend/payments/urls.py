from django.urls import path
from . import views

urlpatterns = [
    path("package/create/", views.create_package, name="create-package"),
    path("package/", views.list_packages, name="get-list-packages"),
    path("package/admin/", views.list_all_packages, name="get-list-all-packages"),
    path("create/", views.create_payment, name="create-payment"),
    path("admin/pending/", views.pending_transactions, name="get-transactions-pending"),
    path("admin/<int:transaction_id>/confirm/", views.confirm_payment, name="confirm-payment"),
    path("checking/<int:transaction_id>/", views.check_payment, name="get-payment-status"),
]