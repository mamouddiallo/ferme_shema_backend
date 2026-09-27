from apps.accounts.models import RoleUtilisateur
from apps.accounts.permissions import EstAuthentifie


class PeutCreerDepense(EstAuthentifie):
    """Enregistrer une dépense courante ou en demander l'approbation."""

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class PeutConsulterFinance(EstAuthentifie):
    """Consultation des données financières — sensible, pas ouvert à tous les rôles."""

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.COMPTABLE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES
