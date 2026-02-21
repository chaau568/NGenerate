from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notifications"),
    path("<int:notification_id>/", views.notification_detail, name="notification-detail"),
]