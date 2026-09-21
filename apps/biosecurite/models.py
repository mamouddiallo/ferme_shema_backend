import uuid

from django.conf import settings
from django.db import models

from apps.elevage.models import BandeChair, BandePondeuse

_CHK_BANDE_CIBLE = models.Q(bande_pondeuse__isnull=False) | models.Q(bande_chair__isnull=False)


class TypeIntervention(models.TextChoices):
    VACCINATION = "vaccination", "Vaccination"
    TRAITEMENT = "traitement", "Traitement"
    VISITE_VETERINAIRE = "visite_veterinaire", "Visite vétérinaire"


class NiveauGravite(models.TextChoices):
    FAIBLE = "faible", "Faible"
    MOYENNE = "moyenne", "Moyenne"
    CRITIQUE = "critique", "Critique"


class InterventionVeterinaire(models.Model):
    """Registre vétérinaire (vaccinations, traitements, visites) — §5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande_pondeuse = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, blank=True, null=True)
    bande_chair = models.ForeignKey(BandeChair, on_delete=models.CASCADE, blank=True, null=True)
    date_intervention = models.DateField()
    type_intervention = models.CharField(max_length=30, choices=TypeIntervention.choices)
    produit = models.CharField(max_length=150, blank=True, null=True)
    dose = models.CharField(max_length=100, blank=True, null=True)
    observation = models.TextField(blank=True, null=True)
    cout = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "biosecurite_interventions_veterinaires"
        constraints = [models.CheckConstraint(condition=_CHK_BANDE_CIBLE, name="chk_bande_cible")]
        indexes = [models.Index(fields=["date_intervention"], name="idx_interventions_date")]

    def __str__(self) -> str:
        cible = self.bande_pondeuse or self.bande_chair
        return f"{self.get_type_intervention_display()} — {cible} ({self.date_intervention})"


class IncidentSanitaire(models.Model):
    """Signalement immédiat de mortalité inhabituelle ou suspicion de maladie — §5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande_pondeuse = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, blank=True, null=True)
    bande_chair = models.ForeignKey(BandeChair, on_delete=models.CASCADE, blank=True, null=True)
    date_incident = models.DateField()
    description = models.TextField()
    gravite = models.CharField(max_length=20, choices=NiveauGravite.choices, default=NiveauGravite.MOYENNE)
    resolu = models.BooleanField(default=False)
    signale_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "biosecurite_incidents_sanitaires"
        constraints = [models.CheckConstraint(condition=_CHK_BANDE_CIBLE, name="chk_bande_cible_incident")]
        indexes = [models.Index(fields=["resolu"], name="idx_incidents_resolu")]

    def __str__(self) -> str:
        cible = self.bande_pondeuse or self.bande_chair
        return f"Incident {self.get_gravite_display()} — {cible} ({self.date_incident})"
