from django.utils import timezone

from django.contrib.auth import authenticate, get_user_model
from .serializers import RegisterSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from .serializers import ProfileUpdateSerializer
from django.contrib.auth.hashers import check_password

User = get_user_model()

auth_response_schema = inline_serializer(
    name="AuthResponse",
    fields={
        "access": serializers.CharField(),
        "refresh": serializers.CharField(),
    },
)


@extend_schema(
    summary="ลงทะเบียนผู้ใช้ใหม่",
    description="สร้างบัญชีผู้ใช้ใหม่ด้วย Email และ Password พร้อมรับ Token สำหรับเข้าใช้งานทันที",
    request=RegisterSerializer,
    responses={201: auth_response_schema},
    tags=["Authentication"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="เข้าสู่ระบบด้วย Email/Password",
    request=inline_serializer(
        name="LoginRequest",
        fields={
            "email": serializers.EmailField(),
            "password": serializers.CharField(),
        },
    ),
    responses={
        200: auth_response_schema,
        400: inline_serializer(
            name="LoginError", fields={"error": serializers.CharField()}
        ),
        403: inline_serializer(
            name="LoginForbidden", fields={"error": serializers.CharField()}
        ),
    },
    tags=["Authentication"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def normal_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, email=email.lower(), password=password)

    if not user:
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_active or user.status != "activate":
        return Response(
            {"error": "Account not active"}, status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="เข้าสู่ระบบด้วย Google",
    request=inline_serializer(
        name="GoogleLoginRequest", fields={"id_token": serializers.CharField()}
    ),
    responses={200: auth_response_schema},
    tags=["Authentication"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    token = request.data.get("id_token")

    if not token:
        return Response(
            {"error": "id_token required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        if not idinfo.get("email_verified"):
            return Response(
                {"error": "Email not verified"}, status=status.HTTP_400_BAD_REQUEST
            )

        email = idinfo["email"].lower()

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

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )

    except ValueError:
        return Response(
            {"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="เชื่อมต่อบัญชีกับ Google",
    description="ใช้สำหรับยืนยันตัวตนด้วย Google ID Token เพื่อเชื่อมต่อหรือตรวจสอบความถูกต้องของอีเมลที่ใช้ในระบบ",
    request=inline_serializer(
        name="ConnectGoogleRequest",
        fields={
            "id_token": serializers.CharField(help_text="ID Token ที่ได้รับจาก Google SDK")
        },
    ),
    responses={
        200: inline_serializer(
            name="ConnectGoogleSuccess", fields={"message": serializers.CharField()}
        ),
        400: inline_serializer(
            name="ConnectGoogleError", fields={"error": serializers.CharField()}
        ),
    },
    tags=["User Profile"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def connect_google(request):
    token = request.data.get("id_token")
    if not token:
        return Response(
            {"error": "id_token required"}, status=status.HTTP_400_BAD_REQUEST
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
            {"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="ดึงข้อมูลโปรไฟล์ผู้ใช้",
    description="ดึงข้อมูลส่วนตัวของผู้ใช้ที่กำลัง Login อยู่ รวมถึงจำนวน Credit ที่เหลือ",
    responses={
        200: inline_serializer(
            name="ProfileResponse",
            fields={
                "user_id": serializers.IntegerField(),
                "email": serializers.EmailField(),
                "username": serializers.CharField(),
                "role": serializers.CharField(),
                "status": serializers.CharField(),
                "credits": serializers.IntegerField(),
            },
        )
    },
    tags=["User Profile"],
)
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user

    if request.method == "DELETE":

        if not user.has_usable_password():
            return Response(
                {"detail": "You must set a password before deleting account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        password = request.data.get("password")

        if not password:
            return Response(
                {"password": "Password is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not check_password(password, user.password):
            return Response(
                {"password": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PUT":
        serializer = ProfileUpdateSerializer(
            user, data=request.data, context={"request": request}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    transaction = (
        user.transactions.filter(
            payment_status="success", expire_at__gte=timezone.now()
        )
        .order_by("-expire_at")
        .first()
    )

    package_name = transaction.package.name if transaction else "free"
    available_credits = user.credit.available if hasattr(user, "credit") else 0
    limit_credits = transaction.package.credits_limit if transaction else 0

    return Response(
        {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "package": package_name,
            "status": user.status,
            "credits": available_credits,
            "limit_credits": limit_credits,
            "has_password": user.has_usable_password(),
        },
        status=status.HTTP_200_OK,
    )
