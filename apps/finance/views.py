from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import EstProprietaire
from apps.audit.mixins import AuditUtilisateurMixin
from apps.finance.events import DepenseApprouvee, DepenseRejetee
from apps.finance.models import Depense, StatutApprobation
from apps.finance.permissions import PeutConsulterFinance, PeutCreerDepense
from apps.finance.serializers import DepenseSerializer
from apps.ventes.models import Vente
from core.events import BusEvenements


class DepenseViewSet(AuditUtilisateurMixin, viewsets.ModelViewSet):
    serializer_class = DepenseSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [PeutConsulterFinance()]
        if self.action in ("approuver", "rejeter"):
            return [EstProprietaire()]
        return [PeutCreerDepense()]

    def get_queryset(self):
        qs = Depense.objects.all().order_by("-date_depense")
        statut = self.request.query_params.get("statut_approbation")
        if statut:
            qs = qs.filter(statut_approbation=statut)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def _changer_statut(self, depense, nouveau_statut):
        if depense.statut_approbation != StatutApprobation.EN_ATTENTE:
            raise ValidationError(
                f"Cette dépense est au statut '{depense.statut_approbation}', pas 'en_attente' — rien à traiter."
            )
        from apps.audit.threadlocal import clear_current_user, set_current_user

        set_current_user(self.request.user)
        try:
            depense.statut_approbation = nouveau_statut
            depense.approuve_par = self.request.user
            depense.save()
        finally:
            clear_current_user()

    @action(detail=True, methods=["post"])
    def approuver(self, request, pk=None):
        """Réservé au propriétaire (§8 : 'autorisation écrite du propriétaire')."""
        depense = self.get_object()
        self._changer_statut(depense, StatutApprobation.APPROUVEE)
        BusEvenements.publier(DepenseApprouvee(depense_id=depense.id, approuve_par_id=request.user.id))
        return Response(DepenseSerializer(depense).data)

    @action(detail=True, methods=["post"])
    def rejeter(self, request, pk=None):
        depense = self.get_object()
        self._changer_statut(depense, StatutApprobation.REJETEE)
        BusEvenements.publier(DepenseRejetee(depense_id=depense.id, rejete_par_id=request.user.id))
        return Response(DepenseSerializer(depense).data)

    @action(detail=False, methods=["get"], permission_classes=[PeutConsulterFinance])
    def compte_exploitation_mensuel(self, request):
        """
        Chiffre d'affaires, dépenses et marge par mois (§10). Répond
        directement à l'une des 5 questions du §15 : "Combien avons-nous
        gagné ?"
        """
        ventes_par_mois = {
            row["mois"].date(): row["total"]
            for row in Vente.objects.annotate(mois=TruncMonth("date_vente"))
            .values("mois")
            .annotate(total=Sum("montant_total"))
        }
        depenses_par_mois = {
            row["mois"]: row["total"]
            for row in Depense.objects.annotate(mois=TruncMonth("date_depense"))
            .values("mois")
            .annotate(total=Sum("montant"))
        }

        tous_les_mois = sorted(set(ventes_par_mois) | set(depenses_par_mois), reverse=True)
        data = [
            {
                "mois": mois,
                "chiffre_affaires": ventes_par_mois.get(mois, 0),
                "total_depenses": depenses_par_mois.get(mois, 0),
                "marge": (ventes_par_mois.get(mois, 0) or 0) - (depenses_par_mois.get(mois, 0) or 0),
            }
            for mois in tous_les_mois
        ]
        return Response(data)
