"""
Tests d'intégration du module finance. Le plus important : vérifier que le
statut d'approbation est bien dérivé automatiquement (pas fourni par le
client) et que seul le propriétaire peut approuver.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.finance.models import Depense, StatutApprobation
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
def gestionnaire(db):
    return Utilisateur.objects.create_user(
        username="gest1", email="g@test.local", password="pass12345", role=RoleUtilisateur.GESTIONNAIRE
    )


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1", email="o@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
    )


@pytest.mark.django_db
class TestCreationDepense:
    def test_ouvrier_ne_peut_pas_creer_de_depense(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/finance/depenses/",
            {"date_depense": "2026-09-22", "categorie": "aliment", "montant": "250000", "type_depense": "courante"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_depense_courante_est_non_requise_automatiquement(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/finance/depenses/",
            {"date_depense": "2026-09-22", "categorie": "aliment", "montant": "250000", "type_depense": "courante"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["statut_approbation"] == StatutApprobation.NON_REQUISE

    def test_depense_exceptionnelle_passe_en_attente_meme_si_le_client_tente_autre_chose(
        self, api_client, gestionnaire
    ):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/finance/depenses/",
            {
                "date_depense": "2026-09-22",
                "categorie": "entretien",
                "montant": "500000",
                "type_depense": "exceptionnelle",
                "statut_approbation": "approuvee",  # tentative ignorée, en lecture seule
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["statut_approbation"] == StatutApprobation.EN_ATTENTE

    def test_investissement_sans_justificatif_est_rejete_par_la_base(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/finance/depenses/",
            {
                "date_depense": "2026-09-22",
                "categorie": "autre",
                "montant": "2000000",
                "type_depense": "investissement",
            },
        )
        # La contrainte CHECK de la base rejette ça (pas de justificatif_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWorkflowApprobation:
    def test_gestionnaire_ne_peut_pas_approuver(self, api_client, gestionnaire):
        depense = Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="entretien",
            montant=500000,
            type_depense="exceptionnelle",
            statut_approbation=StatutApprobation.EN_ATTENTE,
        )
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(f"/api/finance/depenses/{depense.id}/approuver/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_proprietaire_peut_approuver(self, api_client, proprietaire, gestionnaire):
        depense = Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="entretien",
            montant=500000,
            type_depense="exceptionnelle",
            statut_approbation=StatutApprobation.EN_ATTENTE,
        )
        api_client.force_authenticate(user=proprietaire)
        response = api_client.post(f"/api/finance/depenses/{depense.id}/approuver/")
        assert response.status_code == status.HTTP_200_OK
        depense.refresh_from_db()
        assert depense.statut_approbation == StatutApprobation.APPROUVEE
        assert depense.approuve_par == proprietaire

    def test_impossible_de_re_approuver_une_depense_deja_traitee(self, api_client, proprietaire, gestionnaire):
        depense = Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="entretien",
            montant=500000,
            type_depense="exceptionnelle",
            statut_approbation=StatutApprobation.APPROUVEE,
        )
        api_client.force_authenticate(user=proprietaire)
        response = api_client.post(f"/api/finance/depenses/{depense.id}/approuver/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_evenement_publie_a_la_creation_en_attente(self, gestionnaire):
        from apps.finance.serializers import DepenseSerializer
        from core.events import BusEvenements

        evenements = []
        BusEvenements.abonner("finance.depense_en_attente_approbation", evenements.append)

        class FakeRequest:
            user = gestionnaire

        serializer = DepenseSerializer(
            data={
                "date_depense": "2026-09-22",
                "categorie": "entretien",
                "montant": "500000",
                "type_depense": "exceptionnelle",
            },
            context={"request": FakeRequest()},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        assert len(evenements) == 1
        assert evenements[0].montant == 500000.0


@pytest.mark.django_db
class TestCompteExploitationMensuel:
    def test_endpoint_calcule_la_marge(self, api_client, gestionnaire):
        client = Client.objects.create(nom="Client Test", type_client=TypeClient.PARTICULIER, limite_credit=0)
        Vente.objects.create(
            client=client,
            utilisateur=gestionnaire,
            mode_paiement="especes",
            montant_total=100000,
            montant_encaisse=100000,
        )
        Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="aliment",
            montant=30000,
            type_depense="courante",
        )

        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get("/api/finance/depenses/compte_exploitation_mensuel/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        ligne = response.data[0]
        assert float(ligne["chiffre_affaires"]) == 100000.0
        assert float(ligne["total_depenses"]) == 30000.0
        assert float(ligne["marge"]) == 70000.0

    def test_ouvrier_ne_peut_pas_consulter_le_compte_exploitation(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.get("/api/finance/depenses/compte_exploitation_mensuel/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
