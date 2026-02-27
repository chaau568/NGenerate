from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if user.status == "deleted":
            raise AuthenticationFailed("User account deleted")

        if not user.is_active:
            raise AuthenticationFailed("User inactive")

        return user
