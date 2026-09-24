from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import EstAuthentifie
from apps.ventes.models import Client, Vente
from apps.ventes.permissions import PeutEncaisser, PeutGererVentes
from apps.ventes.serializers import ClientSerializer, VenteSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by("nom")
    serializer_class = ClientSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutGererVentes()]


class VenteViewSet(viewsets.ModelViewSet):
    serializer_class = VenteSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "creances_clients"):
            return [EstAuthentifie()]
        if self.action in ("update", "partial_update"):
            return [PeutEncaisser()]
        return [PeutGererVentes()]

    def get_queryset(self):
        qs = Vente.objects.all().prefetch_related("lignes").order_by("-date_vente")
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=False, methods=["get"])
    def creances_clients(self, request):
        """Créances en cours par client (§7, §9) : /api/ventes/ventes/creances_clients/"""
        clients = Client.objects.filter(ventes__solde__gt=0).distinct()
        data = [
            {
                "client_id": client.id,
                "client_nom": client.nom,
                "limite_credit": client.limite_credit,
                "solde_total_du": client.ventes.filter(solde__gt=0).aggregate(total=Sum("solde"))["total"] or 0,
            }
            for client in clients
        ]
        return Response(data)
