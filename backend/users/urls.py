from django.urls import path
from .views import normal_login, google_login, profile

urlpatterns = [
    path("login/", normal_login),
    path("login-google/", google_login),
    path("profile/", profile),
]
