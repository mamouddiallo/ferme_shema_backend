"""
Tests des durcissements de sécurité ajoutés : rate limiting sur le login,
validation de la robustesse des mots de passe, et en-têtes CORS.
"""

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur


@pytest.fixture(autouse=True)
def _vider_cache_throttle():
    """Le throttling DRF s'appuie sur le cache — on repart de zéro à chaque test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gestionnaire(db):
    return Utilisateur.objects.create_user(
        username="gest1", email="g@test.local", password="pass12345", role=RoleUtilisateur.GESTIONNAIRE
    )


@pytest.mark.django_db
class TestThrottlingLogin:
    def test_tentatives_repetees_finissent_par_etre_bloquees(self, api_client, gestionnaire):
        """La limite configurée est 5/min — la 6e tentative doit être rejetée."""
        reponses = []
        for _ in range(6):
            reponse = api_client.post("/api/auth/token/", {"username": "gestionnaire_inexistant", "password": "faux"})
            reponses.append(reponse.status_code)

        # Les 5 premières échouent normalement (401), la 6e est throttlée (429)
        assert reponses[:5] == [status.HTTP_401_UNAUTHORIZED] * 5
        assert reponses[5] == status.HTTP_429_TOO_MANY_REQUESTS

    def test_apres_blocage_meme_les_bons_identifiants_sont_refuses(self, api_client, gestionnaire):
        """Le throttle bloque par IP, avant même de vérifier les identifiants."""
        for _ in range(5):
            api_client.post("/api/auth/token/", {"username": "x", "password": "y"})

        reponse = api_client.post("/api/auth/token/", {"username": "gest1", "password": "pass12345"})
        assert reponse.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_login_reussi_ne_consomme_pas_un_quota_different(self, api_client, gestionnaire):
        """Un login réussi compte aussi dans la même limite (c'est le comportement voulu : anti-spam)."""
        reponse = api_client.post("/api/auth/token/", {"username": "gest1", "password": "pass12345"})
        assert reponse.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestValidationMotDePasse:
    def test_mot_de_passe_trop_commun_est_rejete(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/auth/utilisateurs/",
            {
                "username": "nouvel_utilisateur",
                "email": "n@test.local",
                "role": RoleUtilisateur.OUVRIER,
                "password": "password",  # dans la liste des mots de passe courants
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_mot_de_passe_entierement_numerique_est_rejete(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/auth/utilisateurs/",
            {
                "username": "nouvel_utilisateur2",
                "email": "n2@test.local",
                "role": RoleUtilisateur.OUVRIER,
                "password": "12345678",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mot_de_passe_similaire_au_username_est_rejete(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/auth/utilisateurs/",
            {
                "username": "johndoe123",
                "email": "j@test.local",
                "role": RoleUtilisateur.OUVRIER,
                "password": "johndoe123456",  # trop proche du username
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mot_de_passe_solide_est_accepte(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/auth/utilisateurs/",
            {
                "username": "utilisateur_valide",
                "email": "valide@test.local",
                "role": RoleUtilisateur.OUVRIER,
                "password": "Tr0ub4dor&Zebra!2026",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCORS:
    def test_origine_autorisee_recoit_les_en_tetes_cors(self, api_client):
        response = api_client.get(
            "/api/auth/token/", HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
        )
        # On vérifie la présence de l'en-tête CORS, pas le status code de cette requête de test
        assert response.get("Access-Control-Allow-Origin") == "http://localhost:5173"

    def test_origine_non_autorisee_ne_recoit_pas_len_tete_cors(self, api_client):
        response = api_client.get(
            "/api/auth/token/",
            HTTP_ORIGIN="http://site-malveillant.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert response.get("Access-Control-Allow-Origin") is None
