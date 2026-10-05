# File: backend/config/settings.py
# Purpose: Django settings: apps, middleware, database (SQLite), DRF defaults, CORS and feedback
#     tuning.
# Contents:
#   - env_bool / env_list: helpers that read booleans and comma-separated lists from environment
#     variables.
#   - SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS_*: come from DJANGO_* / CORS_* env vars with dev-safe
#     defaults, so a plain runserver still works.
#   - REST_FRAMEWORK: token + session authentication, IsAuthenticated by default,
#     StandardPagination, JSON-only renderer.
#   - FEEDBACK_WINDOW_DAYS / FEEDBACK_SUMMARY_WINDOW / FEEDBACK_SUMMARY_MIN_RESPONSES: tunable
#     feedback rules (30 days, last 10 sessions, minimum 3 reviews).

"""
CDA Unified Backend - Development Settings

Convention notes for contributors:
- All apps use the `core` base classes (serializers, permissions, pagination)
- Request audit middleware attaches the current user to thread-local storage
- All API endpoints are versioned under /api/v1/
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent



def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Values come from the environment (see backend/.env.example); the defaults keep
# a plain `python manage.py runserver` working without any configuration.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-do-not-use-in-production"
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Project apps
    "core",
    "accounts",
    "classes",
    "feedback.apps.FeedbackConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.RequestAuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF Configuration ---

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
}

# --- CORS ---

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)  # Dev only
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")

# --- Feedback feature ---

FEEDBACK_WINDOW_DAYS = int(os.environ.get("FEEDBACK_WINDOW_DAYS", 30))
FEEDBACK_SUMMARY_WINDOW = int(os.environ.get("FEEDBACK_SUMMARY_WINDOW", 10))
FEEDBACK_SUMMARY_MIN_RESPONSES = int(os.environ.get("FEEDBACK_SUMMARY_MIN_RESPONSES", 3))
