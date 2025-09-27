from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = SignupSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
