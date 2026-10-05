from django.db.models import Case, DecimalField, F, Value, When
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import EstAuthentifie
from apps.elevage.events import BandeChairCloturee
from apps.elevage.models import BandeChair, BandePondeuse, StatutBande, SuiviChair, SuiviPondeuse
from apps.elevage.permissions import PeutGererBandes, PeutSaisirSuivi
from apps.elevage.serializers import (
    BandeChairSerializer,
    BandePondeuseSerializer,
    ClotureBandeChairSerializer,
    SuiviChairSerializer,
    SuiviPondeuseSerializer,
)
from core.events import BusEvenements


class BandePondeuseViewSet(viewsets.ModelViewSet):
    queryset = BandePondeuse.objects.all().order_by("-date_mise_en_place")
    serializer_class = BandePondeuseSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutGererBandes()]


class SuiviPondeuseViewSet(viewsets.ModelViewSet):
    serializer_class = SuiviPondeuseSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "kpi"):
            return [EstAuthentifie()]
        return [PeutSaisirSuivi()]

    def get_queryset(self):
        qs = SuiviPondeuse.objects.all().order_by("-date_suivi")
        bande_id = self.request.query_params.get("bande")
        if bande_id:
            qs = qs.filter(bande_id=bande_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=False, methods=["get"])
    def kpi(self, request):
        """
        Taux de ponte et taux de mortalité par jour (§4, §9, §11).
        Filtrable par bande : /api/elevage/suivi-pondeuse/kpi/?bande=<id>
        """
        qs = self.get_queryset().annotate(
            taux_ponte_pct=Case(
                When(effectif_debut=0, then=Value(0)),
                default=F("oeufs_produits") * 100.0 / F("effectif_debut"),
                output_field=DecimalField(max_digits=6, decimal_places=2),
            ),
            taux_mortalite_pct=Case(
                When(effectif_debut=0, then=Value(0)),
                default=F("mortalite") * 100.0 / F("effectif_debut"),
                output_field=DecimalField(max_digits=6, decimal_places=2),
            ),
        )
        data = [
            {
                "bande_id": row.bande_id,
                "date_suivi": row.date_suivi,
                "effectif_debut": row.effectif_debut,
                "oeufs_produits": row.oeufs_produits,
                "taux_ponte_pct": round(float(row.taux_ponte_pct), 2),
                "mortalite": row.mortalite,
                "taux_mortalite_pct": round(float(row.taux_mortalite_pct), 2),
                "aliment_distribue_kg": row.aliment_distribue_kg,
            }
            for row in qs
        ]
        return Response(data)


class BandeChairViewSet(viewsets.ModelViewSet):
    queryset = BandeChair.objects.all().order_by("-date_arrivee")
    serializer_class = BandeChairSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutGererBandes()]

    @action(detail=True, methods=["post"])
    def cloturer(self, request, pk=None):
        """
        Clôture une bande de chair à la vente (§4, backlog E5) : enregistre
        les infos finales, passe le statut à 'terminee', et publie
        l'événement BandeChairCloturee sur le bus interne.
        """
        bande = self.get_object()
        serializer = ClotureBandeChairSerializer(data=request.data, context={"bande": bande})
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        bande.date_vente = donnees["date_vente"]
        bande.nombre_vendu = donnees["nombre_vendu"]
        bande.poids_vendu_kg = donnees["poids_vendu_kg"]
        bande.chiffre_affaires = donnees["chiffre_affaires"]
        bande.statut = StatutBande.TERMINEE
        bande.save()

        BusEvenements.publier(
            BandeChairCloturee(
                horodatage=timezone.now(),
                bande_id=bande.id,
                nombre_vendu=bande.nombre_vendu,
                chiffre_affaires=float(bande.chiffre_affaires),
            )
        )

        return Response(BandeChairSerializer(bande).data)


class SuiviChairViewSet(viewsets.ModelViewSet):
    serializer_class = SuiviChairSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutSaisirSuivi()]

    def get_queryset(self):
        qs = SuiviChair.objects.all().order_by("-date_suivi")
        bande_id = self.request.query_params.get("bande")
        if bande_id:
            qs = qs.filter(bande_id=bande_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
