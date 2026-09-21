from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

# En dev, les erreurs Celery ne doivent jamais bloquer une requête HTTP
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true"  # noqa: F405
