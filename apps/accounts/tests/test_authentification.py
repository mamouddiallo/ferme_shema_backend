"""
Tests d'intégration : login/refresh/logout, et surtout que les permissions
par rôle bloquent réellement l'accès non autorisé (pas juste qu'elles
existent dans le code).
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import RoleUtilisateur, Utilisateur


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gestionnaire(db):
    return Utilisateur.objects.create_user(
        username="gestionnaire1",
        email="gestionnaire@fermeshema.test",
        password="motdepasse123",
        role=RoleUtilisateur.GESTIONNAIRE,
    )


@pytest.fixture
def ouvrier(db):
    return Utilisateur.objects.create_user(
        username="ouvrier1",
        email="ouvrier@fermeshema.test",
        password="motdepasse123",
        role=RoleUtilisateur.OUVRIER,
    )


@pytest.mark.django_db
class TestAuthentification:
    def test_login_renvoie_access_et_refresh_avec_role(self, api_client, gestionnaire):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "gestionnaire1", "password": "motdepasse123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_echoue_avec_mauvais_mot_de_passe(self, api_client, gestionnaire):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "gestionnaire1", "password": "mauvais_mdp"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_donne_un_nouvel_access_token(self, api_client, gestionnaire):
        login = api_client.post(
            "/api/auth/token/",
            {"username": "gestionnaire1", "password": "motdepasse123"},
        )
        refresh_token = login.data["refresh"]

        response = api_client.post("/api/auth/token/refresh/", {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_logout_invalide_le_refresh_token(self, api_client, gestionnaire):
        login = api_client.post(
            "/api/auth/token/",
            {"username": "gestionnaire1", "password": "motdepasse123"},
        )
        refresh_token = login.data["refresh"]

        logout = api_client.post("/api/auth/logout/", {"refresh": refresh_token})
        assert logout.status_code == status.HTTP_205_RESET_CONTENT

        # Le même refresh token ne doit plus jamais fonctionner après logout
        retry = api_client.post("/api/auth/token/refresh/", {"refresh": refresh_token})
        assert retry.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPermissionsUtilisateurs:
    def test_ouvrier_ne_peut_pas_lister_les_utilisateurs(self, api_client, ouvrier):
        api_client.force_authenticate(user=ouvrier)
        response = api_client.get("/api/auth/utilisateurs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_gestionnaire_peut_lister_les_utilisateurs(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.get("/api/auth/utilisateurs/")
        assert response.status_code == status.HTTP_200_OK

    def test_gestionnaire_peut_creer_un_utilisateur(self, api_client, gestionnaire):
        api_client.force_authenticate(user=gestionnaire)
        response = api_client.post(
            "/api/auth/utilisateurs/",
            {
                "username": "nouvel_ouvrier",
                "email": "nouvel_ouvrier@fermeshema.test",
                "role": RoleUtilisateur.OUVRIER,
                "password": "motdepasse123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        # Le mot de passe doit être hashé, jamais stocké en clair
        utilisateur = Utilisateur.objects.get(username="nouvel_ouvrier")
        assert utilisateur.password != "motdepasse123"
        assert utilisateur.check_password("motdepasse123")

    def test_anonyme_ne_peut_rien_faire(self, api_client):
        response = api_client.get("/api/auth/utilisateurs/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
