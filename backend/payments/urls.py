from django.urls import path
from payments.views import create_package, list_packages, list_all_packages, create_payment, pending_transactions,confirm_payment

urlpatterns = [
    path("package/create/", create_package, name="create-package"),
    path("package/list/", list_packages, name="get-list-packages"),
    path("package/admin/list/", list_all_packages, name="get-list-all-packages"),
    path("create/", create_payment, name="create-payment"),
    path("admin/pending/", pending_transactions, name="get-transactions-pending"),
    path("admin/<int:transaction_id>/confirm/", confirm_payment, name="confirm-payment"),
]