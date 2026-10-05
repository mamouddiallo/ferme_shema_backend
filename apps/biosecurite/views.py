from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import EstAuthentifie
from apps.biosecurite.models import IncidentSanitaire, InterventionVeterinaire
from apps.biosecurite.permissions import PeutEnregistrerIntervention, PeutSignalerIncident
from apps.biosecurite.serializers import IncidentSanitaireSerializer, InterventionVeterinaireSerializer


class InterventionVeterinaireViewSet(viewsets.ModelViewSet):
    queryset = InterventionVeterinaire.objects.all().order_by("-date_intervention")
    serializer_class = InterventionVeterinaireSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutEnregistrerIntervention()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class IncidentSanitaireViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSanitaireSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "non_resolus"):
            return [EstAuthentifie()]
        return [PeutSignalerIncident()]

    def get_queryset(self):
        qs = IncidentSanitaire.objects.all().order_by("-date_incident")
        resolu = self.request.query_params.get("resolu")
        if resolu is not None:
            qs = qs.filter(resolu=resolu.lower() in ("true", "1"))
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=False, methods=["get"])
    def non_resolus(self, request):
        """Raccourci pour le tableau de bord (§9, backlog B3) : /incidents/non_resolus/"""
        qs = IncidentSanitaire.objects.filter(resolu=False).order_by("-date_incident")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
