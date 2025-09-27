from rest_framework import generics
from .models import Users
from .serializers import UsersSerializer

class UsersCreateView(generics.CreateAPIView):
    queryset = Users.objects.all()
    serializer_class = UsersSerializer
