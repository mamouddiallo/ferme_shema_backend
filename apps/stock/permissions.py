from apps.accounts.models import RoleUtilisateur
from apps.accounts.permissions import EstAuthentifie


class PeutGererStock(EstAuthentifie):
    """
    Gérer le catalogue d'articles et faire l'inventaire physique (§6) :
    réservé à l'encadrement. Les mouvements automatiques (déclenchés par une
    vente via le bus d'événements) contournent cette permission puisqu'ils
    sont créés directement par le listener, pas via l'API.
    """

    ROLES_AUTORISES = {
        RoleUtilisateur.PROPRIETAIRE,
        RoleUtilisateur.GESTIONNAIRE,
        RoleUtilisateur.RESPONSABLE_ELEVAGE,
    }

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.ROLES_AUTORISES
