from .base import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True  # les tâches Celery s'exécutent en synchrone pendant les tests

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # hash rapide, tests uniquement
