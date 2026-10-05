import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class RoleUtilisateur(models.TextChoices):
    PROPRIETAIRE = "proprietaire", "Propriétaire"
    GESTIONNAIRE = "gestionnaire", "Gestionnaire"
    RESPONSABLE_ELEVAGE = "responsable_elevage", "Responsable élevage"
    OUVRIER = "ouvrier", "Ouvrier"
    COMPTABLE = "comptable", "Comptable"


class UtilisateurManager(UserManager):
    """
    `createsuperuser` ne demande par défaut que username/email/password — il
    ignore royalement notre champ `role` métier, qui reste alors vide ("").
    Résultat concret et sournois : un superuser Django (is_superuser=True)
    se voit refuser l'accès par nos permissions par rôle, puisqu'aucune
    d'elles ne vérifie is_superuser, seulement request.user.role.

    On corrige ça à la source : tout superuser reçoit le rôle Propriétaire
    par défaut, sauf s'il est explicitement précisé autrement.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", RoleUtilisateur.PROPRIETAIRE)
        return super().create_superuser(username, email, password, **extra_fields)


class Utilisateur(AbstractUser):
    """
    Étend AbstractUser plutôt que de repartir de zéro : on garde gratuitement
    username/email/password/is_active/last_login, et on ajoute le rôle métier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=RoleUtilisateur.choices)

    objects = UtilisateurManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "utilisateurs"
        indexes = [models.Index(fields=["role"], name="idx_utilisateurs_role")]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
