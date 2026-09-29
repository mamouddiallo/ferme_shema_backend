from apps.accounts.models import RoleUtilisateur
from apps.accounts.permissions import EstAuthentifie


class PeutGererVentes(EstAuthentifie):
    """Créer/annuler une vente : l'équipe commerciale et l'encadrement."""

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES


class PeutEncaisser(EstAuthentifie):
    """
    Enregistrer un encaissement (mise à jour de montant_encaisse) : inclut le
    comptable, volontairement — §14 exige qu'une fonction comptabilité
    puisse contrôler les encaissements de façon indépendante du responsable
    qui a réalisé la vente.
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.COMPTABLE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES
