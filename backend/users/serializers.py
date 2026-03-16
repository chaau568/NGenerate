import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from users.services.email_validator import validate_email_exists

User = get_user_model()

# ── Password Regex ────────────────────────────────────────────────────────────
#
# กฎ password:
# - ความยาว 11-50 ตัวอักษร
# - มีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว  [A-Z]
# - มีตัวพิมพ์เล็กอย่างน้อย 1 ตัว  [a-z]
# - มีตัวเลขอย่างน้อย 1 ตัว         [0-9]
# - มีอักขระพิเศษอย่างน้อย 1 ตัว   [!@#$%^&*(),.?":{}|<>]
#
PASSWORD_REGEX = re.compile(
    r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]).{11,50}$'
)

PASSWORD_RULES = (
    "Password must be 11–50 characters and contain at least: "
    "1 uppercase letter, 1 lowercase letter, 1 digit, and 1 special character "
    "(!@#$%^&* etc.)"
)


def validate_password_strength(value: str) -> str:
    """
    ใช้ได้ทั้งใน RegisterSerializer และ ProfileUpdateSerializer
    """
    if not PASSWORD_REGEX.match(value):
        raise serializers.ValidationError(PASSWORD_RULES)
    return value


# ── RegisterSerializer ────────────────────────────────────────────────────────


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "username", "password", "confirm_password")

    def validate_email(self, value):
        # 1. normalize
        value = value.lower().strip()

        # 2. เช็ค domain มีจริง + ไม่ใช่ disposable
        value = validate_email_exists(value)

        # 3. ห้ามซ้ำ (เฉพาะ account ที่ active อยู่)
        existing = User.objects.filter(email__iexact=value).first()
        if existing and existing.status != "deleted":
            raise serializers.ValidationError("This email is already registered.")

        return value

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        email = validated_data["email"]
        password = validated_data["password"]
        username = validated_data.get("username")

        # ถ้า email เคย soft-delete ไปแล้ว → reactivate แทนสร้างใหม่
        deleted_user = User.objects.filter(
            email__iexact=email, status="deleted"
        ).first()

        if deleted_user:
            deleted_user.status = "activate"
            deleted_user.is_active = True
            deleted_user.set_password(password)
            if username:
                deleted_user.username = username
            deleted_user.save(
                update_fields=[
                    "status",
                    "is_active",
                    "password",
                    "username",
                    "updated_at",
                ]
            )
            return deleted_user

        return User.objects.create_user(**validated_data)


# ── ProfileUpdateSerializer ───────────────────────────────────────────────────


class ProfileUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ("email", "username", "old_password", "new_password")

    def validate_email(self, value):
        user = self.context["request"].user
        value = value.lower().strip()

        # เช็ค domain มีจริง
        value = validate_email_exists(value)

        # ห้ามซ้ำกับ user อื่น
        if User.objects.filter(email__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        user = self.context["request"].user
        old_pw = data.get("old_password")
        new_pw = data.get("new_password")

        updating_sensitive = any(
            field in data for field in ["username", "email", "new_password"]
        )

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
        validated_data.pop("old_password", None)

        if new_password:
            instance.set_password(new_password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
