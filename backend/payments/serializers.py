from rest_framework import serializers
from .models import Package


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            "id",
            "name",
            "price",
            "credits_limit",
            "duration_days",
            "is_active",
            "create_at",
            "update_at",
        ]
        read_only_fields = ["id", "create_at", "update_at"]