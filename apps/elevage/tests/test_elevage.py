"""
Tests d'intégration du module élevage. On vérifie que les règles métier du
§4 sont réellement appliquées par l'API, pas seulement documentées.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.elevage.models import BandeChair, BandePondeuse, StatutBande, SuiviPondeuse


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1", email="o@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
    )


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
def bande_pondeuse(db):
    return BandePondeuse.objects.create(
        nom="Bande A", date_mise_en_place="2026-01-01", effectif_initial=500, souche="ISA Brown"
    )


@pytest.fixture
def bande_chair(db):
    return BandeChair.objects.create(
        nom="Bande Chair 1", date_arrivee="2026-01-01", effectif_initial=1000, souche="Cobb 500"
    )


@pytest.mark.django_db
class TestPermissionsBandes:
    def test_ouvrier_ne_peut_pas_creer_une_bande(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/elevage/bandes-pondeuses/",
            {"nom": "Bande X", "date_mise_en_place": "2026-01-01", "effectif_initial": 100},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_gestionnaire_peut_creer_une_bande(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/elevage/bandes-pondeuses/",
            {"nom": "Bande X", "date_mise_en_place": "2026-01-01", "effectif_initial": 100},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_comptable_peut_lire_mais_pas_creer(self, api_client, comptable, bande_pondeuse):
        api_client.force_authenticate(user=comptable)
        lecture = api_client.get("/api/elevage/bandes-pondeuses/")
        assert lecture.status_code == status.HTTP_200_OK

        creation = api_client.post(
            "/api/elevage/bandes-pondeuses/",
            {"nom": "Bande Y", "date_mise_en_place": "2026-01-01", "effectif_initial": 100},
        )
        assert creation.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSuiviPondeuseSaisie:
    def test_ouvrier_peut_saisir_le_suivi_journalier(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 498,
                "mortalite": 1,
                "oeufs_produits": 430,
                "oeufs_casses": 5,
                "oeufs_vendus": 400,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        # stock_oeufs_restant calculé automatiquement : 430 - 5 - 400 = 25
        assert response.data["stock_oeufs_restant"] == 25
        # saisi_par est bien renseigné automatiquement, pas fourni par le client
        suivi = SuiviPondeuse.objects.get(id=response.data["id"])
        assert suivi.saisi_par == ouvrier

    def test_double_saisie_meme_jour_est_rejetee_proprement(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        payload = {
            "bande": str(bande_pondeuse.id),
            "date_suivi": "2026-09-22",
            "effectif_debut": 498,
            "mortalite": 1,
            "oeufs_produits": 430,
        }
        premiere = api_client.post("/api/elevage/suivi-pondeuse/", payload)
        assert premiere.status_code == status.HTTP_201_CREATED

        deuxieme = api_client.post("/api/elevage/suivi-pondeuse/", payload)
        # Doit être une 400 propre (contrainte gérée), jamais une 500
        assert deuxieme.status_code == status.HTTP_400_BAD_REQUEST

    def test_mortalite_superieure_a_effectif_est_rejetee(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 100,
                "mortalite": 150,  # supérieur à l'effectif : impossible
                "oeufs_produits": 50,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "mortalite" in response.data

    def test_vente_superieure_a_disponible_est_rejetee(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 498,
                "mortalite": 0,
                "oeufs_produits": 100,
                "oeufs_casses": 0,
                "oeufs_vendus": 500,  # bien plus que produit, sans stock de la veille
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "oeufs_vendus" in response.data

    def test_stock_de_la_veille_est_repris_le_lendemain(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        # Jour 1 : 50 œufs produits, 20 vendus -> 30 restants
        jour1 = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 498,
                "oeufs_produits": 50,
                "oeufs_vendus": 20,
            },
        )
        assert jour1.data["stock_oeufs_restant"] == 30

        # Jour 2 : 0 produit, mais 30 vendus (le stock de la veille) -> doit passer
        jour2 = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-23",
                "effectif_debut": 498,
                "oeufs_produits": 0,
                "oeufs_vendus": 30,
            },
        )
        assert jour2.status_code == status.HTTP_201_CREATED
        assert jour2.data["stock_oeufs_restant"] == 0

    def test_kpi_calcule_le_taux_de_ponte(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 500,
                "oeufs_produits": 430,
            },
        )
        response = api_client.get(f"/api/elevage/suivi-pondeuse/kpi/?bande={bande_pondeuse.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["taux_ponte_pct"] == 86.0


@pytest.mark.django_db
class TestClotureBandeChair:
    def test_gestionnaire_peut_cloturer_une_bande(self, api_client, gestionnaire, bande_chair):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            f"/api/elevage/bandes-chair/{bande_chair.id}/cloturer/",
            {
                "date_vente": "2026-02-15",
                "nombre_vendu": 950,
                "poids_vendu_kg": "1850.5",
                "chiffre_affaires": "4750000",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        bande_chair.refresh_from_db()
        assert bande_chair.statut == StatutBande.TERMINEE
        assert bande_chair.nombre_vendu == 950

    def test_cloture_avec_nombre_vendu_superieur_a_effectif_est_rejetee(self, api_client, gestionnaire, bande_chair):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            f"/api/elevage/bandes-chair/{bande_chair.id}/cloturer/",
            {
                "date_vente": "2026-02-15",
                "nombre_vendu": 5000,  # bien plus que l'effectif initial (1000)
                "poids_vendu_kg": "1850.5",
                "chiffre_affaires": "4750000",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ouvrier_ne_peut_pas_cloturer_une_bande(self, api_client, ouvrier, bande_chair):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            f"/api/elevage/bandes-chair/{bande_chair.id}/cloturer/",
            {
                "date_vente": "2026-02-15",
                "nombre_vendu": 950,
                "poids_vendu_kg": "1850.5",
                "chiffre_affaires": "4750000",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cloture_publie_evenement_bande_chair_cloturee(self, api_client, gestionnaire, bande_chair):
        from core.events import BusEvenements

        evenements_recus = []
        BusEvenements.abonner("elevage.bande_chair_cloturee", evenements_recus.append)

        api_client.force_authenticate(user=gestionnaire)
        api_client.post(
            f"/api/elevage/bandes-chair/{bande_chair.id}/cloturer/",
            {
                "date_vente": "2026-02-15",
                "nombre_vendu": 950,
                "poids_vendu_kg": "1850.5",
                "chiffre_affaires": "4750000",
            },
        )

        assert len(evenements_recus) == 1
        assert evenements_recus[0].bande_id == bande_chair.id
        assert evenements_recus[0].nombre_vendu == 950
