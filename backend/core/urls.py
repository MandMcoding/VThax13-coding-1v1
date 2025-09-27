from django.contrib import admin
from django.urls import path, include  # ← include is required

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("authapp.urls")),  # ← points to your auth app
]
