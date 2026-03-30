from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from .serializers import RegisterSerializer, RegisterRequestOTPSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from .serializers import ProfileUpdateSerializer
from django.contrib.auth.hashers import check_password
from users.services.otp_service import OTPService

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# ── Register ──────────────────────────────────────────────────────────────────


# Step 1 — รับข้อมูล validate แล้วส่ง OTP (ยังไม่สร้าง user)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_request_otp(request):
    serializer = RegisterRequestOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]

    # เก็บข้อมูล pending ไว้ใน cache/session ชั่วคราว
    # (ไม่สร้าง user ก่อน เพราะ email ยังไม่ verified)
    cache.set(
        f"register_pending:{email}",
        {
            "email": email,
            "password": serializer.validated_data["password"],
            "username": serializer.validated_data.get("username"),
        },
        timeout=600,
    )  # หมดอายุ 10 นาที

    OTPService.generate_and_send(email=email, purpose="register")

    return Response({"email": email, "message": f"OTP sent to {email}"})


# Step 2 — เช็ค OTP แล้วสร้าง user จริง
@api_view(["POST"])
@permission_classes([AllowAny])
def register_verify_otp(request):
    email = request.data.get("email", "").lower().strip()
    otp_code = request.data.get("otp", "").strip()

    if not email or not otp_code:
        return Response({"error": "email and otp are required"}, status=400)

    is_valid = OTPService.verify(email=email, code=otp_code, purpose="register")
    if not is_valid:
        return Response({"error": "Invalid or expired OTP"}, status=400)

    # ดึงข้อมูลที่เก็บไว้ใน cache
    pending = cache.get(f"register_pending:{email}")
    if not pending:
        return Response(
            {"error": "Registration session expired. Please start over."}, status=400
        )

    # สร้าง user จริง
    user = User.objects.create_user(**pending)
    cache.delete(f"register_pending:{email}")

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    สร้างบัญชีใหม่
    Validation ใน RegisterSerializer:
    - email domain มีจริง (MX record check)
    - email ไม่ซ้ำ
    - password 11-50 ตัว + regex
    - password == confirm_password
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        },
        status=status.HTTP_201_CREATED,
    )


# ── Normal Login ──────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([AllowAny])
def normal_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, email=email.lower(), password=password)

    if not user:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.is_active or user.status != "activate":
        return Response(
            {"error": "Account not active"},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        },
        status=status.HTTP_200_OK,
    )


# ── Google Login — Step 1: verify Google token → ส่ง OTP ─────────────────────


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    """
    Step 1 ของ Google Login 2FA

    Request:  { "id_token": "..." }
    Response: { "email": "user@gmail.com", "message": "OTP sent to your email" }

    หลักการ:
    1. verify Google id_token — ถ้าผิดจะ raise ValueError
    2. ดึง email จาก Google token (ยืนยันแล้วโดย Google)
    3. ส่ง OTP ไปที่ email นั้น
    4. Return email กลับไปให้ frontend เก็บไว้ใช้ใน Step 2
    """
    token = request.data.get("id_token")

    if not token:
        return Response(
            {"error": "id_token required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        if not idinfo.get("email_verified"):
            return Response(
                {"error": "Google email not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = idinfo["email"].lower()

        # ส่ง OTP ไปที่ email
        OTPService.generate_and_send(email=email, purpose="google_login")

        return Response(
            {
                "email": email,
                "message": f"OTP has been sent to {email}. Please check your inbox.",
            },
            status=status.HTTP_200_OK,
        )

    except ValueError:
        return Response(
            {"error": "Invalid Google token"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.exception(f"google_login error: {e}")
        return Response(
            {"error": "Failed to send OTP. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── Google Login — Step 2: verify OTP → JWT ───────────────────────────────────


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login_verify_otp(request):
    """
    Step 2 ของ Google Login 2FA

    Request:  { "email": "user@gmail.com", "otp": "123456" }
    Response: { "access": "...", "refresh": "..." }

    หลักการ:
    1. เช็ค OTP ถูกต้องไหม (OTPService.verify)
    2. สร้าง/หา User จาก email
    3. คืน JWT
    """
    email = request.data.get("email", "").lower().strip()
    otp_code = request.data.get("otp", "").strip()

    if not email or not otp_code:
        return Response(
            {"error": "email and otp are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # เช็ค OTP
    is_valid = OTPService.verify(email=email, code=otp_code, purpose="google_login")

    if not is_valid:
        return Response(
            {"error": "Invalid or expired OTP. Please try again."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # สร้าง/หา user จาก email
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email.split("@")[0],
            "status": "activate",
            "is_active": True,
        },
    )

    if created:
        user.set_unusable_password()
        user.save()

    if not user.is_active or user.status != "activate":
        return Response(
            {"error": "Account is not active"},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        },
        status=status.HTTP_200_OK,
    )


# ── Connect Google ────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def connect_google(request):
    token = request.data.get("id_token")
    if not token:
        return Response(
            {"error": "id_token required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        google_email = idinfo["email"].lower()

        if google_email != request.user.email:
            return Response(
                {"error": "Google email does not match your account email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Successfully connected with Google"})

    except ValueError:
        return Response(
            {"error": "Invalid Google token"},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ── Profile ───────────────────────────────────────────────────────────────────


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user

    if request.method == "DELETE":
        if not user.has_usable_password():
            return Response(
                {"detail": "You must set a password before deleting account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password")
        if not password:
            return Response(
                {"password": "Password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_password(password, user.password):
            return Response(
                {"password": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PUT":
        serializer = ProfileUpdateSerializer(
            user, data=request.data, context={"request": request}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    available_credits = user.credit.available if hasattr(user, "credit") else 0

    return Response(
        {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "status": user.status,
            "credits": available_credits,
            "has_password": user.has_usable_password(),
        },
        status=status.HTTP_200_OK,
    )
