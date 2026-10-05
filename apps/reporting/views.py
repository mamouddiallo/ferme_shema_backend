from datetime import date, datetime

from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reporting.exports import generer_excel_rapport_mensuel, generer_pdf_rapport_mensuel
from apps.reporting.permissions import PeutConsulterReporting
from apps.reporting.services import construire_rapport_mensuel, construire_tableau_de_bord, semaine_par_defaut


def _parser_date(valeur: str, nom_champ: str) -> date:
    try:
        return datetime.strptime(valeur, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError({nom_champ: "Format attendu : YYYY-MM-DD."}) from exc


def _parser_mois(valeur: str) -> date:
    try:
        return datetime.strptime(valeur, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise ValidationError({"mois": "Format attendu : YYYY-MM."}) from exc


class TableauDeBordView(APIView):
    """
    Tableau de bord hebdomadaire (§9). Par défaut, les 7 derniers jours.
    Paramètres optionnels : ?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD
    """

    permission_classes = [PeutConsulterReporting]

    def get(self, request):
        date_debut_str = request.query_params.get("date_debut")
        date_fin_str = request.query_params.get("date_fin")

        if date_debut_str and date_fin_str:
            date_debut = _parser_date(date_debut_str, "date_debut")
            date_fin = _parser_date(date_fin_str, "date_fin")
        elif date_debut_str or date_fin_str:
            raise ValidationError("date_debut et date_fin doivent être fournis ensemble, ou aucun des deux.")
        else:
            date_debut, date_fin = semaine_par_defaut()

        if date_debut > date_fin:
            raise ValidationError("date_debut ne peut pas être postérieure à date_fin.")

        return Response(construire_tableau_de_bord(date_debut, date_fin))


class RapportMensuelView(APIView):
    """
    Rapport mensuel en JSON (§10). ?mois=YYYY-MM (par défaut : mois en cours).
    Pour un export fichier, voir RapportMensuelExportView.
    """

    permission_classes = [PeutConsulterReporting]

    def get(self, request):
        mois_str = request.query_params.get("mois")
        mois = _parser_mois(mois_str) if mois_str else date.today().replace(day=1)
        return Response(construire_rapport_mensuel(mois))


class RapportMensuelExportView(APIView):
    """
    Export téléchargeable du rapport mensuel (backlog R2).
    ?mois=YYYY-MM&type_export=pdf|excel (pdf par défaut)

    Le paramètre s'appelle `type_export`, PAS `format` : DRF réserve déjà
    `format` pour sa propre négociation de contenu (suffixes .json, .api...)
    et lève un Http404 si sa valeur ne correspond à aucun renderer connu.
    """

    permission_classes = [PeutConsulterReporting]

    def get(self, request):
        mois_str = request.query_params.get("mois")
        mois = _parser_mois(mois_str) if mois_str else date.today().replace(day=1)
        type_export = request.query_params.get("type_export", "pdf").lower()

        rapport = construire_rapport_mensuel(mois)
        nom_fichier = f"rapport-mensuel-{mois:%Y-%m}"

        if type_export == "pdf":
            contenu = generer_pdf_rapport_mensuel(rapport)
            content_type = "application/pdf"
            extension = "pdf"
        elif type_export == "excel":
            contenu = generer_excel_rapport_mensuel(rapport)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:
            raise ValidationError({"type_export": "Valeurs acceptées : 'pdf' ou 'excel'."})

        response = HttpResponse(contenu, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{nom_fichier}.{extension}"'
        return response
