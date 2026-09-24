from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import EstAuthentifie
from apps.stock.models import Article, InventairePhysique, MouvementStock
from apps.stock.permissions import PeutGererStock
from apps.stock.serializers import ArticleSerializer, InventairePhysiqueSerializer, MouvementStockSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by("nom")
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "sous_seuil"):
            return [EstAuthentifie()]
        return [PeutGererStock()]

    @action(detail=False, methods=["get"])
    def sous_seuil(self, request):
        """Articles dont le stock actuel est sous leur seuil d'alerte (§6, backlog S4)."""
        qs = (
            Article.objects.filter(actif=True)
            .annotate(
                entrees=Coalesce(
                    Sum("mouvements__quantite", filter=Q(mouvements__type_mouvement="entree")),
                    0,
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                sorties=Coalesce(
                    Sum("mouvements__quantite", filter=Q(mouvements__type_mouvement="sortie")),
                    0,
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
            )
            .filter(entrees__lte=F("sorties") + F("seuil_alerte"))
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class MouvementStockViewSet(viewsets.ModelViewSet):
    serializer_class = MouvementStockSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstAuthentifie()]
        return [PeutGererStock()]

    def get_queryset(self):
        qs = MouvementStock.objects.all().order_by("-date_mouvement")
        article_id = self.request.query_params.get("article")
        if article_id:
            qs = qs.filter(article_id=article_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class InventairePhysiqueViewSet(viewsets.ModelViewSet):
    serializer_class = InventairePhysiqueSerializer
    permission_classes = [PeutGererStock]

    def get_queryset(self):
        qs = InventairePhysique.objects.all().order_by("-date_inventaire")
        article_id = self.request.query_params.get("article")
        if article_id:
            qs = qs.filter(article_id=article_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
