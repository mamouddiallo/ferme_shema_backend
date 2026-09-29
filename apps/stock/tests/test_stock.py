"""
Tests d'intégration du module stock. Le plus important : vérifier que
l'écouteur d'événement décrémente réellement le stock quand une vente est
publiée sur le bus, en passant par le vrai flux (publication -> listener ->
création du mouvement), pas en appelant la fonction Python directement.
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.stock.models import Article, CategorieArticle, MouvementStock
from apps.ventes.events import LigneVenteEvenement, VenteEnregistree
from core.events import BusEvenements


@pytest.fixture
def api_client():
    return APIClient()


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


@pytest.fixture
def article_plateau(db):
    return Article.objects.create(
        nom="Plateau 30 œufs", categorie=CategorieArticle.PLATEAU_OEUFS, unite="unité", seuil_alerte=50
    )


@pytest.mark.django_db
class TestPermissionsStock:
    def test_ouvrier_ne_peut_pas_creer_un_article(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/stock/articles/", {"nom": "Aliment ponte", "categorie": "aliment", "unite": "kg"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_gestionnaire_peut_creer_un_article(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/stock/articles/", {"nom": "Aliment ponte", "categorie": "aliment", "unite": "kg"}
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestInventairePhysique:
    def test_ecart_sans_justification_est_rejete(self, api_client, gestionnaire, article_plateau):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/stock/inventaires/",
            {
                "article": str(article_plateau.id),
                "date_inventaire": "2026-09-22",
                "quantite_theorique": "100",
                "quantite_physique": "95",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "justification" in response.data

    def test_ecart_avec_justification_est_accepte(self, api_client, gestionnaire, article_plateau):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/stock/inventaires/",
            {
                "article": str(article_plateau.id),
                "date_inventaire": "2026-09-22",
                "quantite_theorique": "100",
                "quantite_physique": "95",
                "justification": "5 plateaux cassés lors de la manutention",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        # L'écart est calculé par la base, jamais fourni par le client
        assert float(response.data["ecart"]) == -5.0

    def test_sans_ecart_aucune_justification_requise(self, api_client, gestionnaire, article_plateau):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/stock/inventaires/",
            {
                "article": str(article_plateau.id),
                "date_inventaire": "2026-09-22",
                "quantite_theorique": "100",
                "quantite_physique": "100",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestSeuilAlerte:
    def test_article_sous_seuil_apparait_dans_lendpoint(self, api_client, gestionnaire, article_plateau):
        # Seuil à 50, on ne met que 10 en stock (entrée) -> sous le seuil
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=10
        )
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get("/api/stock/articles/sous_seuil/")
        assert response.status_code == status.HTTP_200_OK
        assert any(a["id"] == str(article_plateau.id) for a in response.data)

    def test_article_au_dessus_du_seuil_absent_de_lendpoint(self, api_client, gestionnaire, article_plateau):
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=200
        )
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get("/api/stock/articles/sous_seuil/")
        assert not any(a["id"] == str(article_plateau.id) for a in response.data)


@pytest.mark.django_db
class TestDecrementAutomatiqueParEvenement:
    """
    Vérifie le flux complet : publication de l'événement (comme le fera le
    module Ventes) -> écouteur Stock -> création réelle du mouvement.
    """

    def test_vente_publiee_decremente_le_stock(self, gestionnaire, article_plateau):
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=100
        )

        BusEvenements.publier(
            VenteEnregistree(
                vente_id=uuid.uuid4(),
                utilisateur_id=gestionnaire.id,
                client_id=None,
                montant_total=45000,
                lignes=[LigneVenteEvenement(produit="Plateau 30 œufs", quantite=15)],
            )
        )

        mouvement = MouvementStock.objects.filter(article=article_plateau, type_mouvement="sortie").first()
        assert mouvement is not None
        assert float(mouvement.quantite) == 15.0
        assert mouvement.utilisateur == gestionnaire

    def test_produit_sans_article_correspondant_ne_plante_pas(self, gestionnaire):
        """Le nom du produit vendu ne correspond à aucun article : ignoré proprement, pas de crash."""
        # Ne doit lever aucune exception
        BusEvenements.publier(
            VenteEnregistree(
                vente_id=uuid.uuid4(),
                utilisateur_id=gestionnaire.id,
                lignes=[LigneVenteEvenement(produit="Produit inexistant", quantite=5)],
            )
        )
        assert MouvementStock.objects.count() == 0

    def test_utilisateur_introuvable_ne_plante_pas(self, article_plateau):
        BusEvenements.publier(
            VenteEnregistree(
                vente_id=uuid.uuid4(),
                utilisateur_id=uuid.uuid4(),  # n'existe pas
                lignes=[LigneVenteEvenement(produit="Plateau 30 œufs", quantite=5)],
            )
        )
        assert MouvementStock.objects.count() == 0

    def test_stock_actuel_reflete_le_decrement(self, api_client, gestionnaire, article_plateau):
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=100
        )
        BusEvenements.publier(
            VenteEnregistree(
                vente_id=uuid.uuid4(),
                utilisateur_id=gestionnaire.id,
                lignes=[LigneVenteEvenement(produit="Plateau 30 œufs", quantite=15)],
            )
        )

        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get(f"/api/stock/articles/{article_plateau.id}/")
        assert response.data["stock_actuel"] == 85.0
