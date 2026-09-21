import uuid

from django.conf import settings
from django.db import models


class StatutBande(models.TextChoices):
    ACTIVE = "active", "Active"
    TERMINEE = "terminee", "Terminée"
    SUSPENDUE = "suspendue", "Suspendue"


class BandePondeuse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    date_mise_en_place = models.DateField()
    effectif_initial = models.PositiveIntegerField()
    souche = models.CharField(max_length=100, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=StatutBande.choices, default=StatutBande.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elevage_bandes_pondeuses"
        constraints = [
            models.CheckConstraint(condition=models.Q(effectif_initial__gt=0), name="chk_effectif_initial_positif"),
        ]

    def __str__(self) -> str:
        return self.nom


class SuiviPondeuse(models.Model):
    """Registre journalier d'une bande de pondeuses — champs minimum imposés au §4."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, related_name="suivis")
    date_suivi = models.DateField()
    effectif_debut = models.PositiveIntegerField()
    mortalite = models.PositiveIntegerField(default=0)
    aliment_distribue_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    eau_consommee_l = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    oeufs_produits = models.PositiveIntegerField(default=0)
    oeufs_casses = models.PositiveIntegerField(default=0)
    oeufs_vendus = models.PositiveIntegerField(default=0)
    stock_oeufs_restant = models.PositiveIntegerField(default=0)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elevage_suivi_pondeuse"
        constraints = [
            models.UniqueConstraint(fields=["bande", "date_suivi"], name="uq_suivi_pondeuse_bande_date"),
        ]
        indexes = [models.Index(fields=["bande", "date_suivi"], name="idx_suivi_pondeuse_bande_date")]

    def __str__(self) -> str:
        return f"{self.bande.nom} — {self.date_suivi}"


class BandeChair(models.Model):
    """Fiche de bande de poulets de chair — inclut les infos de clôture/vente (§4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    date_arrivee = models.DateField()
    effectif_initial = models.PositiveIntegerField()
    souche = models.CharField(max_length=100, blank=True, null=True)
    poids_initial_g = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=StatutBande.choices, default=StatutBande.ACTIVE)
    # Clôture de bande, renseignée à la vente
    date_vente = models.DateField(blank=True, null=True)
    nombre_vendu = models.PositiveIntegerField(blank=True, null=True)
    poids_vendu_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    chiffre_affaires = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elevage_bandes_chair"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(effectif_initial__gt=0), name="chk_effectif_initial_chair_positif"
            ),
        ]

    def __str__(self) -> str:
        return self.nom


class SuiviChair(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande = models.ForeignKey(BandeChair, on_delete=models.CASCADE, related_name="suivis")
    date_suivi = models.DateField()
    poids_moyen_g = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    aliment_distribue_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    mortalite = models.PositiveIntegerField(default=0)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elevage_suivi_chair"
        constraints = [
            models.UniqueConstraint(fields=["bande", "date_suivi"], name="uq_suivi_chair_bande_date"),
        ]

    def __str__(self) -> str:
        return f"{self.bande.nom} — {self.date_suivi}"
