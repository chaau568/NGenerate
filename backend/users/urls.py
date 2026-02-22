from django.urls import path
from .views import register, normal_login, google_login, connect_google, profile

urlpatterns = [
    path("register/", register),
    path("login/", normal_login),
    path("login-google/", google_login),
    path("connect-google/", connect_google),
    path("profile/", profile),
]
