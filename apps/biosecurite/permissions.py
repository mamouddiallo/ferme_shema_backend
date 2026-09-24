from apps.accounts.models import RoleUtilisateur
from apps.accounts.permissions import EstAuthentifie


class PeutSignalerIncident(EstAuthentifie):
    """
    Signaler un incident sanitaire (§5 : 'signaler immédiatement toute
    mortalité inhabituelle') est un devoir de terrain — ouvert à tous les
    rôles opérationnels, y compris les ouvriers qui sont les premiers à
    remarquer un problème.
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
        RoleUtilisateur.OUVRIER,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class PeutEnregistrerIntervention(EstAuthentifie):
    """
    Enregistrer une intervention vétérinaire (vaccination, traitement) est un
    acte plus formel, avec un coût associé — réservé à l'encadrement, pas à
    un simple ouvrier.
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES
