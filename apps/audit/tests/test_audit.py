"""
Tests d'intégration du module audit. Le point le plus délicat à vérifier :
que l'utilisateur JWT authentifié est correctement attribué à chaque entrée,
malgré le piège du thread-local expliqué dans threadlocal.py.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.audit.models import JournalAudit
from apps.finance.models import Depense, StatutApprobation
from apps.stock.models import Article, CategorieArticle, MouvementStock
from apps.ventes.models import Client, TypeClient


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
def client_resto(db):
    return Client.objects.create(nom="Chez Fatou", type_client=TypeClient.RESTAURANT, limite_credit=100000)


@pytest.fixture
def article_plateau(db):
    return Article.objects.create(
        nom="Plateau 30 œufs", categorie=CategorieArticle.PLATEAU_OEUFS, unite="unité", seuil_alerte=10
    )


@pytest.mark.django_db
class TestJournalisationAutomatique:
    def test_creation_vente_est_journalisee_avec_le_bon_utilisateur(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "45000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        entree = JournalAudit.objects.filter(entite="ventes.Vente", action="CREATE").first()
        assert entree is not None
        assert entree.utilisateur == gestionnaire
        assert (
            entree.nouvelle_valeur["montant_total"] == "45000.00"
            or float(entree.nouvelle_valeur["montant_total"]) == 45000.0
        )

    def test_mouvement_stock_automatique_hemet_via_evenement_est_aussi_journalise(
        self, api_client, gestionnaire, client_resto, article_plateau
    ):
        MouvementStock.objects.create(
            article=article_plateau, utilisateur=gestionnaire, type_mouvement="entree", quantite=100
        )
        api_client.force_authenticate(user=gestionnaire)
        api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "45000",
                "lignes": [{"produit": "Plateau 30 œufs", "quantite": 15, "prix_unitaire": "3000"}],
            },
            format="json",
        )
        # Le mouvement de sortie auto-créé par le bus d'événements doit lui
        # aussi apparaître dans le journal, attribué au même utilisateur.
        # On identifie précisément CE mouvement (pas celui du fixture de
        # setup) par son type, pour ne pas dépendre d'un ordre implicite.
        entrees_mouvement = JournalAudit.objects.filter(entite="stock.MouvementStock", action="CREATE")
        entree_sortie = next(
            (e for e in entrees_mouvement if e.nouvelle_valeur.get("type_mouvement") == "sortie"), None
        )
        assert entree_sortie is not None
        assert entree_sortie.utilisateur == gestionnaire

    def test_modification_capture_ancienne_et_nouvelle_valeur(self, api_client, proprietaire, gestionnaire):
        depense = Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="entretien",
            montant=500000,
            type_depense="exceptionnelle",
            statut_approbation=StatutApprobation.EN_ATTENTE,
        )
        api_client.force_authenticate(user=proprietaire)
        api_client.post(f"/api/finance/depenses/{depense.id}/approuver/")

        entree = JournalAudit.objects.filter(entite="finance.Depense", action="UPDATE").first()
        assert entree is not None
        assert entree.utilisateur == proprietaire
        assert entree.ancienne_valeur["statut_approbation"] == "en_attente"
        assert entree.nouvelle_valeur["statut_approbation"] == "approuvee"

    def test_lecture_seule_ne_cree_aucune_entree(self, api_client, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        JournalAudit.objects.all().delete()
        api_client.get("/api/ventes/ventes/")
        assert JournalAudit.objects.count() == 0


@pytest.mark.django_db
class TestPermissionsJournal:
    def test_ouvrier_ne_peut_pas_consulter_le_journal(self, api_client):
        ouvrier = Utilisateur.objects.create_user(
            username="ouv1", email="ouv@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
        )
        api_client.force_authenticate(user=ouvrier)
        response = api_client.get("/api/audit/journal/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_gestionnaire_ne_peut_pas_consulter_le_journal(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get("/api/audit/journal/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_proprietaire_peut_consulter_le_journal(self, api_client, proprietaire, gestionnaire, client_resto):
        api_client.force_authenticate(user=gestionnaire)
        api_client.post(
            "/api/ventes/ventes/",
            {
                "client": str(client_resto.id),
                "mode_paiement": "especes",
                "montant_encaisse": "10000",
                "lignes": [{"produit": "Test", "quantite": 1, "prix_unitaire": "10000"}],
            },
            format="json",
        )
        api_client.force_authenticate(user=proprietaire)
        response = api_client.get("/api/audit/journal/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1 if isinstance(response.data, dict) else len(response.data) >= 1

    def test_journal_est_en_lecture_seule_meme_pour_le_proprietaire(self, api_client, proprietaire):
        response = api_client.post(
            "/api/audit/journal/",
            {"action": "CREATE", "entite": "test.Fake"},
        )
        api_client.force_authenticate(user=proprietaire)
        response = api_client.post(
            "/api/audit/journal/",
            {"action": "CREATE", "entite": "test.Fake"},
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
