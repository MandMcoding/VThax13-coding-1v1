from django.urls import path
from .views import SignupView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
]
