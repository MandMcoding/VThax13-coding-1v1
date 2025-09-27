"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta
import os

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------------------
# Security / Debug
# --------------------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-^hodx@vnx_2=7c+*yauooqe5dc%2xhg7@lfhxxp^38zk@r1#io")
DEBUG = True

# Frontend dev host(s)
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# If you access Django (admin, etc.) from Vite origin, trust it for CSRF (use HTTPS in prod)
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]

# --------------------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",
    "channels",

    # Local apps
    "game",
    "authapp",   # <-- your signup/login app (create with `startapp accounts`)
]

# --------------------------------------------------------------------------------------
# Middleware
# NOTE: CORS middleware must be placed as high as possible, before CommonMiddleware.
# --------------------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --------------------------------------------------------------------------------------
# URLs / Templates
# --------------------------------------------------------------------------------------
ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# WSGI for traditional HTTP; ASGI for HTTP + WebSockets (Channels)
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# --------------------------------------------------------------------------------------
# Channels (in-memory for dev; switch to Redis in prod)
# --------------------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# --------------------------------------------------------------------------------------
# Database (PostgreSQL)
# --------------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "hack_db",       # or "postgres" if you didn’t make a new db yet
        "USER": "appuser",    # or your macOS username if that’s what `psql` shows
        "PASSWORD": "StrongPWHere",        # leave empty if no password is set
        "HOST": "127.0.0.1",             # local end of SSH tunnel
        "PORT": "5433",
    }
}

# --------------------------------------------------------------------------------------
# REST framework + JWT (SimpleJWT)
# --------------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # In dev you can leave open; tighten per-view in prod
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# --------------------------------------------------------------------------------------
# CORS (dev-friendly; restrict in prod)
# --------------------------------------------------------------------------------------
# Simplest: allow all during local development
CORS_ALLOW_ALL_ORIGINS = True

# Or, safer alternative:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:5173",
# ]

# --------------------------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# I18N / TZ
# --------------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------------------
STATIC_URL = "static/"

# --------------------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
