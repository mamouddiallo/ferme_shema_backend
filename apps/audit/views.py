from rest_framework import viewsets

from apps.accounts.permissions import EstProprietaire
from apps.audit.models import JournalAudit
from apps.audit.serializers import JournalAuditSerializer


class JournalAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consultation du journal d'audit — jamais de création/modification/
    suppression via l'API : les entrées ne sont écrites que par les signaux
    (apps.audit.signals), jamais à la main.
    """

    serializer_class = JournalAuditSerializer
    permission_classes = [EstProprietaire]

    def get_queryset(self):
        qs = JournalAudit.objects.all().order_by("-date_action")
        entite = self.request.query_params.get("entite")
        if entite:
            qs = qs.filter(entite=entite)
        entite_id = self.request.query_params.get("entite_id")
        if entite_id:
            qs = qs.filter(entite_id=entite_id)
        return qs
