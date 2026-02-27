from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "username", "password", "confirm_password")

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return data

    def validate_email(self, value):
        value = value.lower()

        existing_user = User.objects.filter(email__iexact=value).first()

        if existing_user and existing_user.status != "deleted":
            raise serializers.ValidationError("Email already exists")

        return value

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        email = validated_data["email"]
        password = validated_data["password"]
        username = validated_data.get("username")

        deleted_user = User.objects.filter(
            email__iexact=email,
            status="deleted"
        ).first()

        if deleted_user:
            deleted_user.status = "activate"
            deleted_user.is_active = True
            deleted_user.set_password(password)

            if username:
                deleted_user.username = username

            deleted_user.save(update_fields=[
                "status",
                "is_active",
                "password",
                "username",
                "updated_at"
            ])

            return deleted_user

        return User.objects.create_user(**validated_data)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False, min_length=8)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ("email", "username", "old_password", "new_password")

    def validate_email(self, value):
        user = self.context["request"].user
        value = value.lower()
        if User.objects.filter(email__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, data):
        user = self.context["request"].user
        old_pw = data.get("old_password")
        new_pw = data.get("new_password")

        updating_sensitive = any(field in data for field in ["username", "email", "new_password"])
        
        if not updating_sensitive:
            return data

        if not user.has_usable_password():
            if new_pw:
                return data
            raise serializers.ValidationError(
                {"detail": "You must set a password first before editing profile."}
            )

        if not old_pw:
            raise serializers.ValidationError(
                {"old_password": "Current password is required to make changes."}
            )

        if not check_password(old_pw, user.password):
            raise serializers.ValidationError(
                {"old_password": "The original password is incorrect."}
            )

        return data

    def update(self, instance, validated_data):
        new_password = validated_data.pop("new_password", None)
        if new_password:
            instance.set_password(new_password)
        
        for attr, value in validated_data.items():
            if attr != "old_password":
                setattr(instance, attr, value)
        
        instance.save()
        return instance
