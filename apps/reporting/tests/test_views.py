"""
Tests des vues reporting. On vérifie les permissions, la validation des
paramètres, et surtout que les fichiers exportés sont de vrais PDF/Excel
valides — pas juste une réponse 200 vide de sens.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.finance.models import Depense
from apps.ventes.models import Client, TypeClient, Vente


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def proprietaire(db):
    return Utilisateur.objects.create_user(
        username="prop1", email="p@test.local", password="pass12345", role=RoleUtilisateur.PROPRIETAIRE
    )


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1", email="o@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
    )


@pytest.mark.django_db
class TestPermissionsReporting:
    def test_ouvrier_ne_peut_pas_consulter_le_tableau_de_bord(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.get("/api/reporting/tableau-de-bord/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_proprietaire_peut_consulter_le_tableau_de_bord(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/tableau-de-bord/")
        assert response.status_code == status.HTTP_200_OK
        assert "semaine" in response.data
        assert "cumul_mensuel" in response.data


@pytest.mark.django_db
class TestValidationParametres:
    def test_date_debut_seule_sans_date_fin_est_rejetee(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/tableau-de-bord/?date_debut=2026-09-01")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_date_debut_apres_date_fin_est_rejetee(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/tableau-de-bord/?date_debut=2026-09-30&date_fin=2026-09-01")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_format_mois_invalide_est_rejete(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/rapport-mensuel/?mois=septembre-2026")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_format_export_invalide_est_rejete(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/rapport-mensuel/export/?type_export=csv")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestExportFichiers:
    def test_export_pdf_renvoie_un_vrai_pdf(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/rapport-mensuel/export/?mois=2026-09&type_export=pdf")
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        assert "rapport-mensuel-2026-09.pdf" in response["Content-Disposition"]

    def test_export_excel_renvoie_un_vrai_fichier_xlsx(self, api_client, proprietaire):
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/reporting/rapport-mensuel/export/?mois=2026-09&type_export=excel")
        assert response.status_code == status.HTTP_200_OK
        assert response.content.startswith(b"PK")  # signature d'archive zip (format .xlsx)
        assert "rapport-mensuel-2026-09.xlsx" in response["Content-Disposition"]

    def test_export_reflete_les_vraies_donnees(self, api_client, proprietaire):
        client = Client.objects.create(nom="Client Export", type_client=TypeClient.PARTICULIER, limite_credit=0)
        Vente.objects.create(
            client=client,
            utilisateur=proprietaire,
            date_vente="2026-09-15T10:00:00Z",
            mode_paiement="especes",
            montant_total=200000,
            montant_encaisse=200000,
        )
        Depense.objects.create(utilisateur=proprietaire, date_depense="2026-09-10", categorie="aliment", montant=50000)

        api_client.force_authenticate(user=proprietaire)
        response_json = api_client.get("/api/reporting/rapport-mensuel/?mois=2026-09")
        assert float(response_json.data["chiffre_affaires"]) == 200000.0
        assert float(response_json.data["marge"]) == 150000.0

        response_pdf = api_client.get("/api/reporting/rapport-mensuel/export/?mois=2026-09&type_export=pdf")
        assert len(response_pdf.content) > 1000  # un PDF avec du contenu réel, pas un fichier vide
