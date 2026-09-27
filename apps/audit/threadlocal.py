"""
Un signal Django (pre_save/post_save/post_delete) n'a pas accès à la requête
HTTP, donc pas à request.user. Un middleware classique ne convient pas non
plus ici : avec JWT, l'authentification DRF s'exécute à l'intérieur du cycle
de la vue, après le passage des middlewares Django — un middleware capturerait
donc systématiquement un utilisateur anonyme.

La solution : chaque ViewSet concerné pose explicitement l'utilisateur
courant ici (via AuditUtilisateurMixin) juste avant d'déclencher une
sauvegarde, puis le retire aussitôt après.
"""

import threading

_local = threading.local()


def set_current_user(user) -> None:
    _local.user = user


def get_current_user():
    return getattr(_local, "user", None)


def clear_current_user() -> None:
    _local.user = None
