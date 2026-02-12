from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

User = get_user_model()

@api_view(['POST'])
def normal_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response({"error": "Invalid credentials"}, status=400)

    if user.status != "activate":
        return Response({"error": "Account not active"}, status=403)

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    })
    
@api_view(['POST'])
def google_login(request):
    token = request.data.get("id_token")

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        if not idinfo.get("email_verified"):
            return Response({"error": "Email not verified"}, status=400)

        email = idinfo['email']

        user = User.objects.filter(email=email).first()

        if not user:
            base_username = email.split("@")[0]
            username = base_username

            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=email,
                status="activate"
            )

        if user.status != "activate":
            return Response({"error": "Account not active"}, status=403)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })

    except ValueError:
        return Response({"error": "Invalid Google token"}, status=400)
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({
        "user_id": request.user.id,
        "username": request.user.username
    })
