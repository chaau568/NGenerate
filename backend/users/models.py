from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        if not extra_fields.get("username"):
            extra_fields["username"] = email.split("@")[0]
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "activate")
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("user", "User"),
    )

    STATUS_CHOICES = (
        ("activate", "Activate"),
        ("deleted", "Deleted"),
        ("suspended", "Suspended"),
    )

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="activate")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"email: {self.email} | username: {self.username}"

    def edit(self, **extra_fields):
        for field, value in extra_fields.items():
            if hasattr(self, field):
                if field in ["username", "email", "password"] and (
                    value is None or value == ""
                ):
                    raise ValueError(
                        f"{field.capitalize()} invalid format (cannot be empty)"
                    )
                if field == "role":
                    valid_roles = [choice[0] for choice in self.ROLE_CHOICES]
                    if value not in valid_roles:
                        raise ValueError(f"Role '{value}' is invalid")
                if field == "status":
                    valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
                    if value not in valid_statuses:
                        raise ValueError(f"Status '{value}' is invalid")
                if field == "password":
                    self.set_password(value)
                else:
                    setattr(self, field, value)
        self.save()
        return self

    def soft_delete(self):
        with transaction.atomic():
            self.novels.all().delete()
            self.status = "deleted"
            self.is_active = False
            self.set_unusable_password()
            self.save()


class UserCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="credit")
    available = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(available__gte=0),
                name="credit_available_gte_zero",
            )
        ]

    def __str__(self):
        return f"{self.user.email} | available={self.available}"

    def add_credit(self, amount: int):
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        with transaction.atomic():
            credit = UserCredit.objects.select_for_update().get(pk=self.pk)
            credit.available = F("available") + amount
            credit.save(update_fields=["available"])

    def deduct_credit(self, amount: int):
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        with transaction.atomic():
            credit = UserCredit.objects.select_for_update().get(pk=self.pk)
            if credit.available < amount:
                raise ValueError("Insufficient credits")
            credit.available = F("available") - amount
            credit.save(update_fields=["available"])


# เก็บ OTP สำหรับ Google Login 2FA
class OTPCode(models.Model):

    PURPOSE_CHOICES = (("google_login", "Google Login 2FA"),)  # ใช้ตอน login ด้วย Google

    email = models.EmailField()  # email ที่ส่ง OTP ไป
    code = models.CharField(max_length=10)  # ตัวเลข 6 หลัก
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expire_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "purpose"]),
        ]

    def __str__(self):
        return f"{self.email} | {self.purpose} | used={self.is_used}"

    def is_valid(self) -> bool:
        """เช็คว่า OTP ยังใช้ได้อยู่ไหม (ไม่หมดอายุ + ยังไม่ถูกใช้)"""
        return not self.is_used and timezone.now() < self.expire_at
