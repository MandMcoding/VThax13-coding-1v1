# authapp/serializers.py
from rest_framework import serializers
from .models import Users

class UsersSerializer(serializers.ModelSerializer):
    # client sends plain password; we map it into passwordhash for the demo
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Users
        fields = ["user_id", "fname", "lname", "email", "username", "role", "password"]
        read_only_fields = ["user_id"]

    def validate_email(self, value):
        if Users.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_username(self, value):
        if Users.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        plain = validated_data.pop("password")
        role = validated_data.get("role") or "user"
        user = Users.objects.create(
            **validated_data,
            passwordhash=plain,   # DEMO ONLY — don’t do this in production
            role=role,
        )
        return user

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep.pop("password", None)  # never return password
        return rep
