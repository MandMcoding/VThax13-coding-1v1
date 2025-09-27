# authapp/views.py
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import IntegrityError

from .models import Users
from .serializers import UsersSerializer


class UsersCreateView(generics.CreateAPIView):
    """
    POST /api/users/
    Body:
      {
        "fname": "Alice",        # optional
        "lname": "Johnson",      # optional
        "username": "alicej",    # required, unique
        "email": "a@ex.com",     # required, unique
        "password": "secret",    # required (mapped to passwordhash for demo)
        "role": "user"           # optional, defaults to "user"
      }
    Response: { user_id, username, email, role }
    """
    queryset = Users.objects.all()
    serializer_class = UsersSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            # Let the serializer do the mapping (password -> passwordhash)
            user = ser.save()
        except IntegrityError:
            # Handle unique constraints (username/email)
            return Response(
                {"detail": "Username or email already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        # Serializer hides password/passwordhash in its to_representation
        # but we’ll return a compact payload explicitly:
        return Response(
            {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/login/
    Body: { "email": "...", "password": "..." }
    For the demo we compare against Users.passwordhash directly.
    """
    authentication_classes = []  # no auth required to hit login
    permission_classes = []      # open endpoint

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = (
            Users.objects
            .filter(email=email, passwordhash=password)
            .only("user_id", "username", "role", "email")
            .first()
        )

        if not user:
            return Response({"detail": "Invalid credentials."}, status=401)

        # Return a simple payload (no JWT for the demo)
        return Response(
            {
                "success": True,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "token": "demo-token",  # placeholder if your frontend expects a token
            },
            status=200,
        )
