from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Utilisateur


class FermeShemaTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Étend le serializer JWT standard pour embarquer le rôle métier dans le
    token. Le frontend peut ainsi adapter son affichage sans appel API
    supplémentaire juste après la connexion.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token


class UtilisateurSerializer(serializers.ModelSerializer):
    """
    Création et consultation des comptes utilisateurs.

    Volontairement PAS d'auto-inscription : la création passe uniquement par
    ce serializer, utilisé par un endpoint réservé aux rôles gestionnaires
    (voir permissions.EstGestionnaireOuPlus dans le ViewSet).
    """

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Utilisateur
        fields = ["id", "username", "email", "role", "is_active", "password", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_password(self, valeur):
        # Note : la vérification de similarité avec le username se fait dans
        # validate() ci-dessous, car elle a besoin des DEUX champs ensemble.
        return valeur

    def validate(self, attrs):
        password = attrs.get("password")
        if password:
            # Instance temporaire (non sauvegardée) pour que le validateur de
            # similarité puisse comparer le mot de passe au username/email.
            utilisateur_temporaire = Utilisateur(
                username=attrs.get("username", getattr(self.instance, "username", "")),
                email=attrs.get("email", getattr(self.instance, "email", "")),
            )
            try:
                validate_password(password, user=utilisateur_temporaire)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        utilisateur = Utilisateur(**validated_data)
        utilisateur.set_password(password)  # jamais de mot de passe en clair en base
        utilisateur.save()
        return utilisateur

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
