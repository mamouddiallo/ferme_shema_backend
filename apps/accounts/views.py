from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import Utilisateur
from apps.accounts.permissions import EstGestionnaireOuPlus
from apps.accounts.serializers import FermeShemaTokenObtainPairSerializer, UtilisateurSerializer


class FermeShemaTokenObtainPairView(TokenObtainPairView):
    """Login : renvoie un access token + refresh token, avec le rôle embarqué."""

    serializer_class = FermeShemaTokenObtainPairSerializer
    permission_classes = [AllowAny]


class FermeShemaTokenRefreshView(TokenRefreshView):
    """Renouvelle un access token à partir d'un refresh token encore valide."""

    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    Déconnexion réelle : place le refresh token fourni sur liste noire, pour
    qu'il ne puisse plus jamais générer de nouvel access token, même s'il
    n'a pas encore expiré.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ValidationError({"refresh": "Ce champ est requis."})
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": "Token invalide ou déjà expiré."}) from exc
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    Gestion des comptes utilisateurs. Réservée aux gestionnaires et
    propriétaires (§14 : pas d'auto-inscription, contrôle centralisé).
    """

    queryset = Utilisateur.objects.all().order_by("username")
    serializer_class = UtilisateurSerializer
    permission_classes = [EstGestionnaireOuPlus]
