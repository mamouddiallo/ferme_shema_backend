from apps.audit.threadlocal import clear_current_user, set_current_user


class AuditUtilisateurMixin:
    """
    À ajouter aux ViewSets des modèles suivis par l'audit (§12). Pose
    l'utilisateur courant dans le stockage thread-local juste avant
    perform_create/update/destroy, pour que le signal déclenché par .save()
    puisse l'attribuer correctement à l'entrée du journal.
    """

    def perform_create(self, serializer):
        set_current_user(self.request.user)
        try:
            super().perform_create(serializer)
        finally:
            clear_current_user()

    def perform_update(self, serializer):
        set_current_user(self.request.user)
        try:
            super().perform_update(serializer)
        finally:
            clear_current_user()

    def perform_destroy(self, instance):
        set_current_user(self.request.user)
        try:
            super().perform_destroy(instance)
        finally:
            clear_current_user()
