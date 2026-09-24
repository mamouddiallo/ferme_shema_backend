"""
Tests d'intégration du module ventes. Le test le plus important vérifie le
flux complet : créer une vente via l'API doit réellement décrémenter le
stock, en passant par le vrai bus d'événements — pas un mock.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.stock.models import Article, CategorieArticle, MouvementStock
from apps.ventes.models import Client, TypeClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gestionnaire(db):
    return Utilisateur.objects.create_user(
        username="gest1", email="g@test.local", password="pass12345", role=RoleUtilisateur.GESTIONNAIRE
    )


@pytest.fixture
def comptable(db):
    return Utilisateur.objects.create_user(
        username="compta1", email="c@test.local", password="pass12345", role=RoleUtilisateur.COMPTABLE
    )


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1", email="o@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
    )


@pytest.fixture
def client_resto(db):
    return Client.objects.create(nom="Chez Fatou", type_client=TypeClient.RESTAURANT, limite_credit=100000)


@pytest.fixture
def article_plateau(db):
    return Article.objects.create(
        nom="Plateau 30 œufs", categorie=CategorieArticle.PLATEAU_OEUFS, unite="unité", seuil_alerte=10
    )


@pytest.mark.django_db
class TestCreationVente:
    def test_ouvrier_ne_peut_pas_enregistrer_une_vente(self, api_client, ouvrier, client_resto):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "45000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_montant_total_est_calcule_pas_fourni_par_le_client(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "45000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert float(response.data["montant_total"]) == 45000.0
        assert float(response.data["solde"]) == 0.0

    def test_vente_sans_ligne_est_rejetee(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {"client": str(client_resto.id), "mode_paiement": "especes", "lignes": []},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_encaissement_superieur_au_total_est_rejete(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "999999",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLimiteCredit:
    def test_vente_a_credit_dans_la_limite_est_acceptee(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "0",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 10, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        # 30000 de solde <= 100000 de limite : accepté
        assert response.status_code == status.HTTP_201_CREATED

    def test_vente_qui_depasse_la_limite_est_rejetee(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "0",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 50, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        # 150000 de solde > 100000 de limite : rejeté
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "client" in response.data

    def test_creances_cumulees_sont_prises_en_compte(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        # Première vente à crédit : 60000 de solde (dans la limite de 100000)
        api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "0",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 20, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        # Deuxième vente : 60000 de plus dépasserait la limite (120000 > 100000)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "0",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 20, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSeparationEncaissement:
    def test_comptable_peut_enregistrer_un_encaissement(self, api_client, gestionnaire, comptable, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        creation = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "0",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 10, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        vente_id = creation.data["id"]

        # Le comptable, sans avoir créé la vente, enregistre l'encaissement (§14)
        api_client.force_authenticate(user=comptable)
        response = api_client.patch(f"/api/ventes/ventes/{vente_id}/", {"montant_encaisse": "30000"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert float(response.data["solde"]) == 0.0

    def test_comptable_ne_peut_pas_creer_une_vente(self, api_client, comptable, client_resto):
        api_client.force_authenticate(user=comptable)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 5, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCreancesClients:
    def test_endpoint_liste_les_clients_avec_solde(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "credit",
                "montant_encaisse": "10000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 10, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        response = api_client.get("/api/ventes/ventes/creances_clients/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert float(response.data[0]["solde_total_du"]) == 20000.0


@pytest.mark.django_db
class TestFluxCompletVersStock:
    """Le test qui prouve que tout le circuit fonctionne, pas juste chaque module isolément."""

    def test_creer_une_vente_decremente_reellement_le_stock(
        self, api_client, gestionnaire, client_resto, article_plateau
    ):
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=100
        )

        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "45000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        mouvement_sortie = MouvementStock.objects.filter(article=article_plateau, type_mouvement="sortie").first()
        assert mouvement_sortie is not None
        assert float(mouvement_sortie.quantite) == 15.0

        stock_check = api_client.get(f"/api/stock/articles/{article_plateau.id}/")
        assert stock_check.data["stock_actuel"] == 85.0
