from django.urls import path
from . import views

urlpatterns = [
    path("", views.session_assets, name="session_assets"),
    path("videos/<int:video_id>/delete/", views.delete_video, name="delete_video"),
    path("videos/<int:video_id>/watch/", views.watch_video, name="watch_video"),
    path("videos/<int:video_id>/download/", views.download_video, name="download_video"),
]