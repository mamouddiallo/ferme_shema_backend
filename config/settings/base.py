"""
Settings communs à tous les environnements.
Ne jamais mettre de valeur de secret en dur ici — tout passe par des variables
d'environnement (voir .env.example à la racine).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Charge le fichier .env à la racine du projet dans os.environ.
# Sans ça, un lancement local (venv, hors Docker) ignore silencieusement le
# .env et retombe sur les valeurs par défaut ci-dessous — ce qui a causé une
# connexion silencieuse au mauvais PostgreSQL (natif au lieu du conteneur).
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_results",
    "corsheaders",
    # Modules métier — un module = un bounded context (§ architecture)
    "apps.accounts",
    "apps.elevage",
    "apps.biosecurite",
    "apps.stock",
    "apps.ventes",
    "apps.finance",
    "apps.audit",
    "apps.reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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

# Modèle utilisateur personnalisé avec rôles métier (§14 de l'organigramme)
AUTH_USER_MODEL = "accounts.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# CORS : liste blanche explicite des origines autorisées (le futur frontend),
# jamais CORS_ALLOW_ALL_ORIGINS=True — une API qui manipule des données
# financières ne doit être appelable que depuis des origines connues.
# Format .env : CORS_ALLOWED_ORIGINS=http://localhost:5173,https://app.fermeshema.com
CORS_ALLOWED_ORIGINS = [
    origine.strip()
    for origine in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origine.strip()
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "ferme_shema_backend"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # connexions persistantes, utile en charge
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Limites générales de l'API : généreuses, juste pour éviter un abus grossier
        "anon": "60/min",
        "user": "300/min",
        # Limite spécifique à la connexion (anti brute-force) : bien plus stricte,
        # appliquée en plus des limites générales via LoginRateThrottle
        "login": "5/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Ferme SHEMA",
    "DESCRIPTION": "API de gestion de l'exploitation avicole (élevage, stock, ventes, finance, biosécurité).",
    "VERSION": "1.0.0",
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# --- Celery : bus de tâches asynchrones (rapports, notifications, KPI lourds) ---
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# --- Cache Redis (KPI calculés, rate limiting) ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    }
}

# Seuil de mortalité journalière (%) au-delà duquel une alerte biosécurité
# est automatiquement créée (§5 : "signaler immédiatement toute mortalité
# inhabituelle"). Ajustable par ferme sans toucher au code.
SEUIL_ALERTE_MORTALITE_PCT = float(os.environ.get("SEUIL_ALERTE_MORTALITE_PCT", "5.0"))

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
