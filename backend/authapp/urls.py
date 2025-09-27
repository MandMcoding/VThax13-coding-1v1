from django.urls import path
from .views import UsersCreateView, LoginView   # ← import both

urlpatterns = [
    path("users/", UsersCreateView.as_view(), name="users-create"),
    path("login/", LoginView.as_view(), name="login"),
]
