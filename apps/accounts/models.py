import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class RoleUtilisateur(models.TextChoices):
    PROPRIETAIRE = "proprietaire", "Propriétaire"
    GESTIONNAIRE = "gestionnaire", "Gestionnaire"
    RESPONSABLE_ELEVAGE = "responsable_elevage", "Responsable élevage"
    OUVRIER = "ouvrier", "Ouvrier"
    COMPTABLE = "comptable", "Comptable"


class Utilisateur(AbstractUser):
    """
    Étend AbstractUser plutôt que de repartir de zéro : on garde gratuitement
    username/email/password/is_active/last_login, et on ajoute le rôle métier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=RoleUtilisateur.choices)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "utilisateurs"
        indexes = [models.Index(fields=["role"], name="idx_utilisateurs_role")]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
