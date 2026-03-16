# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.normal_login, name="normal-login"),
    path("login-google/", views.google_login, name="google-login"),
    path("login-google/verify/", views.google_login_verify_otp, name="google-login-verify-otp"),
    path("connect-google/", views.connect_google, name="connect-google"),
    path("profile/", views.profile, name="profile"),
]
