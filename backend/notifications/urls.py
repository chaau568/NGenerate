from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notifications"),
    path("<int:notification_id>/", views.notification_detail, name="notification-detail"),
    path("<int:notification_id>/delete/", views.notification_delete, name="notification-delete"),
    path("<int:notification_id>/update/", views.notification_update, name="notification-update"),
    path("unread-count/", views.get_notification_is_read, name="get-notification-is-read"),
]