from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleUtilisateur
from apps.accounts.permissions import EstAuthentifie


class PeutSaisirSuivi(EstAuthentifie):
    """
    Saisie du registre journalier (§4) : c'est le travail quotidien des
    ouvriers sur le terrain, pas réservé à l'encadrement. Le comptable n'a
    en revanche aucune raison de saisir des données d'élevage.
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
        RoleUtilisateur.OUVRIER,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class PeutGererBandes(BasePermission):
    """
    Créer/clôturer une bande, modifier ses informations de base : réservé à
    l'encadrement (pas à un simple ouvrier), mais la lecture reste ouverte à
    tout utilisateur authentifié (géré séparément dans les ViewSets).
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in self.ROLES_AUTORISES)
