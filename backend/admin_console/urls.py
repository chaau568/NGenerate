from django.urls import path
from . import views

urlpatterns = [
    path("main-dashboard/", views.main_dashboard, name="admin-main-dashboard"),
    path("activity-dashboard/", views.activity_dashboard, name="admin-activity-dashboard"),
]