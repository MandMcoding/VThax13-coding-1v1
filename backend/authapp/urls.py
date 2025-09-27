from django.urls import path
from .views import UsersCreateView

urlpatterns = [
    path("users/", UsersCreateView.as_view(), name="users-create"),
]
