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
            "recommendation",
            "features",
            "is_active",
            "create_at",
            "update_at",
        ]
