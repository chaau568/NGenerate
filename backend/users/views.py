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

User = get_user_model()

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

@api_view(['POST'])
@permission_classes([AllowAny])
def normal_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(
        request,
        email=email.lower(),
        password=password
    )

    if not user:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_active or user.status != "activate":
        return Response(
            {"error": "Account not active"},
            status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )

  
@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    token = request.data.get("id_token")

    if not token:
        return Response(
            {"error": "id_token required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        if not idinfo.get("email_verified"):
            return Response(
                {"error": "Email not verified"},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = idinfo["email"].lower()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@")[0],
                "status": "activate",
                "is_active": True,
            }
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
            {"error": "Invalid Google token"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])  
def connect_google(request):
    token = request.data.get("id_token")
    if not token:
        return Response({"error": "id_token required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        google_email = idinfo["email"].lower()

        if google_email != request.user.email:
            return Response({"error": "Google email does not match your account email"}, 
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Successfully connected with Google"})

    except ValueError:
        return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    available_credits = user.credit.available if hasattr(user, 'credit') else 0
    return Response({
        "user_id": request.user.id,
        "email": request.user.email,
        "username": request.user.username,
        "role": request.user.role,
        "status": request.user.status,
        "credits": available_credits
    })

