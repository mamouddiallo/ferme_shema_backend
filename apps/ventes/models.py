import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


class TypeClient(models.TextChoices):
    PARTICULIER = "particulier", "Particulier"
    RESTAURANT = "restaurant", "Restaurant"
    HOTEL = "hotel", "Hôtel"
    SUPERMARCHE = "supermarche", "Supermarché"
    REVENDEUR = "revendeur", "Revendeur"
    BOULANGERIE = "boulangerie", "Boulangerie"
    AUTRE = "autre", "Autre"


class ModePaiement(models.TextChoices):
    ESPECES = "especes", "Espèces"
    MOBILE_MONEY = "mobile_money", "Mobile money"
    VIREMENT = "virement", "Virement"
    CHEQUE = "cheque", "Chèque"
    CREDIT = "credit", "Crédit"


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    type_client = models.CharField(max_length=20, choices=TypeClient.choices)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    limite_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ventes_clients"

    def __str__(self) -> str:
        return self.nom


class Vente(models.Model):
    """En-tête de vente — date, client, paiement, montants (§7)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="ventes", blank=True, null=True)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_vente = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    montant_encaisse = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    solde = models.GeneratedField(
        expression=F("montant_total") - F("montant_encaisse"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ventes_ventes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(montant_encaisse__lte=F("montant_total")),
                name="chk_encaisse_inferieur_total",
            ),
        ]
        indexes = [models.Index(fields=["client", "date_vente"], name="idx_ventes_client_date")]

    def __str__(self) -> str:
        return f"Vente {self.id} — {self.montant_total} ({self.date_vente:%Y-%m-%d})"


class LigneVente(models.Model):
    """Détail produit/quantité/prix d'une vente (normalisé par rapport au MCD initial)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name="lignes")
    produit = models.CharField(max_length=150)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ligne = models.GeneratedField(
        expression=F("quantite") * F("prix_unitaire"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )

    class Meta:
        db_table = "ventes_lignes"

    def __str__(self) -> str:
        return f"{self.quantite} x {self.produit}"
