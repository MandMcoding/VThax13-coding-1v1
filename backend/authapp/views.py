# authapp/views.py
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection

from .models import Users
from .serializers import UsersSerializer

class UsersCreateView(generics.CreateAPIView):
    """
    POST /api/auth/users/
    Body: { "username": "...", "email": "...", "password": "..." }
    Writes into User.passwordhash (demo: plain text).
    """
    queryset = Users.objects.all()
    serializer_class = UsersSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        username = s.validated_data.get("username")
        email    = s.validated_data.get("email")
        password = s.validated_data.get("password")  # serializer maps to passwordhash

        with connection.cursor() as cur:
            cur.execute(
                'INSERT INTO "User" (username, email, passwordhash, role) VALUES (%s, %s, %s, %s) RETURNING user_id',
                [username, email, password, "user"]
            )
            user_id = cur.fetchone()[0]

        return Response(
            {"user_id": user_id, "username": username, "email": email, "role": "user"},
            status=status.HTTP_201_CREATED
        )

class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)

        with connection.cursor() as cur:
            cur.execute(
                'SELECT user_id, username, role FROM "User" WHERE email=%s AND passwordhash=%s',
                [email, password]
            )
            row = cur.fetchone()

        if not row:
            return Response({"error": "Invalid credentials"}, status=401)

        user_id, username, role = row
        return Response(
            {"message": "Login successful", "user_id": user_id, "username": username, "role": role, "token": "demo-token"},
            status=200
        )
