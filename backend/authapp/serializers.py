from django.contrib.auth.models import User
from rest_framework import serializers

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def create(self, validated_data):
        pwd = validated_data.pop("password")
        return User.objects.create_user(password=pwd, **validated_data)
