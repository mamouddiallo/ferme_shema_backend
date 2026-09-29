"""
Tests d'intégration du module biosécurité. Le plus important : vérifier que
l'alerte automatique fonctionne réellement de bout en bout à travers le bus
d'événements (Élevage publie -> Biosécurité écoute et crée l'incident) sans
qu'aucun des deux modules n'importe l'autre directement.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.biosecurite.models import IncidentSanitaire, NiveauGravite
from apps.elevage.models import BandePondeuse


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1", email="o@test.local", password="pass12345", role=RoleUtilisateur.OUVRIER
    )


@pytest.fixture
def responsable(db):
    return Utilisateur.objects.create_user(
        username="resp1",
        email="r@test.local",
        password="pass12345",
        role=RoleUtilisateur.RESPONSABLE_ELEVAGE,
    )


@pytest.fixture
def bande_pondeuse(db):
    return BandePondeuse.objects.create(
        nom="Bande A", date_mise_en_place="2026-01-01", effectif_initial=500, souche="ISA Brown"
    )


@pytest.mark.django_db
class TestPermissionsBiosecurite:
    def test_ouvrier_peut_signaler_un_incident(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/biosecurite/incidents/",
            {
                "bande_pondeuse": str(bande_pondeuse.id),
                "date_incident": "2026-09-22",
                "description": "Comportement anormal observé sur plusieurs sujets",
                "gravite": "moyenne",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_ouvrier_ne_peut_pas_enregistrer_une_intervention_veterinaire(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/biosecurite/interventions/",
            {
                "bande_pondeuse": str(bande_pondeuse.id),
                "date_intervention": "2026-09-22",
                "type_intervention": "vaccination",
                "produit": "Newcastle",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_responsable_peut_enregistrer_une_intervention(self, api_client, responsable, bande_pondeuse):
        api_client.force_authenticate(user=responsable)
        response = api_client.post(
            "/api/biosecurite/interventions/",
            {
                "bande_pondeuse": str(bande_pondeuse.id),
                "date_intervention": "2026-09-22",
                "type_intervention": "vaccination",
                "produit": "Newcastle",
                "cout": "15000",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_sans_aucune_bande_ciblee_est_rejete(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.post(
            "/api/biosecurite/incidents/",
            {"date_incident": "2026-09-22", "description": "Test", "gravite": "faible"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestIncidentsNonResolus:
    def test_endpoint_ne_retourne_que_les_non_resolus(self, api_client, ouvrier, bande_pondeuse):
        IncidentSanitaire.objects.create(
            bande_pondeuse=bande_pondeuse, date_incident="2026-09-20", description="Résolu", resolu=True
        )
        IncidentSanitaire.objects.create(
            bande_pondeuse=bande_pondeuse, date_incident="2026-09-21", description="Pas résolu", resolu=False
        )
        api_client.force_authenticate(user=ouvrier)
        response = api_client.get("/api/biosecurite/incidents/non_resolus/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["description"] == "Pas résolu"


@pytest.mark.django_db
class TestAlerteAutomatiqueMortalite:
    """
    Le test le plus important de ce module : vérifie que l'événement publié
    par le module Élevage traverse bien le bus jusqu'au module Biosécurité,
    sans import direct entre les deux.
    """

    def test_mortalite_sous_le_seuil_ne_cree_aucun_incident(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        # Seuil par défaut 5% ; ici 1/500 = 0.2%, largement en dessous
        api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 500,
                "mortalite": 1,
                "oeufs_produits": 430,
            },
        )
        assert IncidentSanitaire.objects.count() == 0

    def test_mortalite_au_dessus_du_seuil_cree_un_incident_moyen(self, api_client, ouvrier, bande_pondeuse):
        api_client.force_authenticate(user=ouvrier)
        # 30/500 = 6% > seuil 5%, mais < 10% (2x le seuil) -> gravité moyenne
        response = api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 500,
                "mortalite": 30,
                "oeufs_produits": 400,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        incidents = IncidentSanitaire.objects.filter(bande_pondeuse=bande_pondeuse)
        assert incidents.count() == 1
        incident = incidents.first()
        assert incident.gravite == NiveauGravite.MOYENNE
        assert incident.resolu is False
        assert "30" in incident.description

    def test_mortalite_tres_elevee_cree_un_incident_critique(self, api_client, ouvrier, bande_pondeuse):
        # 60/500 = 12% > 2x le seuil (10%) -> gravité critique
        api_client.force_authenticate(user=ouvrier)
        api_client.post(
            "/api/elevage/suivi-pondeuse/",
            {
                "bande": str(bande_pondeuse.id),
                "date_suivi": "2026-09-22",
                "effectif_debut": 500,
                "mortalite": 60,
                "oeufs_produits": 350,
            },
        )
        incident = IncidentSanitaire.objects.get(bande_pondeuse=bande_pondeuse)
        assert incident.gravite == NiveauGravite.CRITIQUE
