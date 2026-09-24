"""
Permissions par rôle métier (§14 du cahier des charges : organigramme et
séparation des fonctions). Chaque permission vérifie le rôle de
request.user.role — jamais is_staff/is_superuser, qui sont des concepts
Django génériques sans rapport avec nos rôles métier.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleUtilisateur


class EstAuthentifie(BasePermission):
    """Base commune : rejette d'abord tout utilisateur non connecté."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class EstProprietaire(EstAuthentifie):
    """Réservé au(x) compte(s) propriétaire — décisions finales, audit."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == RoleUtilisateur.PROPRIETAIRE


class EstGestionnaireOuPlus(EstAuthentifie):
    """Propriétaire ou gestionnaire — pilotage courant de la ferme."""

    ROLES_AUTORISES = {RoleUtilisateur.PROPRIETAIRE, RoleUtilisateur.GESTIONNAIRE}

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class EstResponsableElevageOuPlus(EstAuthentifie):
    """Propriétaire, gestionnaire ou responsable élevage — saisie terrain encadrée."""

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class EstComptableOuPlus(EstAuthentifie):
    """Propriétaire, gestionnaire ou comptable — accès aux données financières."""

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.COMPTABLE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES
