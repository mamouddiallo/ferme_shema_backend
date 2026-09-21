import uuid

from django.conf import settings
from django.db import models


class TypeDepense(models.TextChoices):
    COURANTE = "courante", "Courante"
    EXCEPTIONNELLE = "exceptionnelle", "Exceptionnelle"
    INVESTISSEMENT = "investissement", "Investissement"


class StatutApprobation(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    APPROUVEE = "approuvee", "Approuvée"
    REJETEE = "rejetee", "Rejetée"
    NON_REQUISE = "non_requise", "Non requise"


class CategorieDepense(models.TextChoices):
    ALIMENT = "aliment", "Aliment"
    MEDICAMENT_SOINS = "medicament_soins", "Médicaments & soins"
    SALAIRES = "salaires", "Salaires"
    EAU_ELECTRICITE = "eau_electricite", "Eau & électricité"
    TRANSPORT = "transport", "Transport"
    ENTRETIEN = "entretien", "Entretien"
    EMBALLAGE = "emballage", "Emballage"
    AUTRE = "autre", "Autre"


class Depense(models.Model):
    """Dépenses avec workflow d'approbation selon le type — §8."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="depenses")
    date_depense = models.DateField()
    categorie = models.CharField(max_length=30, choices=CategorieDepense.choices)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_depense = models.CharField(max_length=20, choices=TypeDepense.choices, default=TypeDepense.COURANTE)
    justificatif_url = models.URLField(max_length=500, blank=True, null=True)
    statut_approbation = models.CharField(
        max_length=20, choices=StatutApprobation.choices, default=StatutApprobation.NON_REQUISE
    )
    approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="depenses_approuvees"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_depenses"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(type_depense=TypeDepense.INVESTISSEMENT)
                | models.Q(justificatif_url__isnull=False),
                name="chk_justificatif_investissement",
            ),
        ]
        indexes = [
            models.Index(fields=["date_depense"], name="idx_depenses_date"),
            models.Index(fields=["categorie"], name="idx_depenses_categorie"),
        ]

    def __str__(self) -> str:
        return f"{self.get_categorie_display()} — {self.montant} ({self.date_depense})"
