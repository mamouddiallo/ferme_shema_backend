# S'assure que l'app Celery est chargée dès le démarrage de Django,
# pour que @shared_task fonctionne dans tous les modules.
from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
