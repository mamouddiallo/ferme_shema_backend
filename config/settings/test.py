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

# Le rate limiting (throttling DRF) s'appuie sur le cache Django. En test, on
# utilise un cache mémoire local plutôt que Redis, pour ne pas dépendre d'un
# service externe — et chaque test démarre avec un cache vide.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
