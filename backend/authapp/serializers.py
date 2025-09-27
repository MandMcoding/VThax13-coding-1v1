# authapp/serializers.py
from rest_framework import serializers
from .models import Users

class UsersSerializer(serializers.ModelSerializer):
    # Incoming field from the client; will be stored in passwordhash
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Users
        # Expose what you need; keep password write-only
        fields = [
            "user_id",
            "fname",
            "lname",
            "email",
            "username",
            "role",
            "password",       # virtual input
            "passwordhash",   # optional: include if you want to see it in admin; usually omit
        ]
        read_only_fields = ["user_id", "passwordhash"]  # don’t let clients set passwordhash directly

    def create(self, validated_data):
        # Pull out the plain password, map to passwordhash
        plain = validated_data.pop("password")
        # default role if not provided
        role = validated_data.get("role") or "user"

        user = Users.objects.create(
            **validated_data,
            passwordhash=plain,   # DEMO ONLY. In real apps, hash this!
            role=role,
        )
        return user

    def to_representation(self, instance):
        """Hide password fields in responses."""
        rep = super().to_representation(instance)
        rep.pop("password", None)
        rep.pop("passwordhash", None)
        return rep
