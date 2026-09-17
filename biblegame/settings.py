"""
Django settings for biblegame project.
Configuration locale + production.
"""

from pathlib import Path
import os
import certifi
import dj_database_url
from decouple import config, Csv

# Certificats SSL
os.environ["SSL_CERT_FILE"] = certifi.where()

# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"



# ============================================================
# SÉCURITÉ
# ============================================================

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-dev-key-change-me"
)

DEBUG = config(
    "DEBUG",
    default=True,
    cast=bool
)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=Csv()
)


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "quiz",
    "accounts",
    "game",
    "bible",
    "pages",
    "dashboard",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Fichiers statiques en production
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS
# ============================================================

ROOT_URLCONF = "biblegame.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
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


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = "biblegame.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": dj_database_url.config(
        default=config(
            "DATABASE_URL",
            default=f"postgresql://postgres:S@127.0.0.1:5432/biblegame"
        ),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ============================================================
# AUTHENTIFICATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/profile/"
LOGOUT_REDIRECT_URL = "/"


# ============================================================
# INTERNATIONALISATION
# ============================================================

LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "Africa/Porto-Novo"

USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)


# ============================================================
# MEDIA
# ============================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# EMAIL — GMAIL
# ============================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587

EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = config(
    "EMAIL_HOST_USER",
    default=""
)

EMAIL_HOST_PASSWORD = config(
    "EMAIL_HOST_PASSWORD",
    default=""
)

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=EMAIL_HOST_USER
)


# ============================================================
# HTTPS / PRODUCTION
# ============================================================

if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"