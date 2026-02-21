from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager
)
from django.utils import timezone
from django.db import transaction

class UserManager(BaseUserManager):    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        
        if not extra_fields.get("username"):
            extra_fields["username"] = email.split("@")[0]
        
        user = self.model(
            email=email,
            **extra_fields
        )
        
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
    username = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

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
        return self.email
    
    def edit(self, **extra_fields):
        for field, value in extra_fields.items():
            if hasattr(self, field):
                if field in ["username", "email", "password"] and (value is None or value == ""):
                    raise ValueError(f"{field.capitalize()} invalid format (cannot be empty)")
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
        
class UserCredit(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="credit"
    )

    available = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} | available={self.available}"
    