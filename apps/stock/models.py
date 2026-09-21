import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


class CategorieArticle(models.TextChoices):
    ALIMENT = "aliment", "Aliment"
    MEDICAMENT = "medicament", "Médicament"
    VACCIN = "vaccin", "Vaccin"
    DESINFECTANT = "desinfectant", "Désinfectant"
    EMBALLAGE = "emballage", "Emballage"
    PLATEAU_OEUFS = "plateau_oeufs", "Plateau d'œufs"
    MATERIEL = "materiel", "Matériel"
    PIECE_RECHANGE = "piece_rechange", "Pièce de rechange"
    AUTRE = "autre", "Autre"


class TypeMouvement(models.TextChoices):
    ENTREE = "entree", "Entrée"
    SORTIE = "sortie", "Sortie"


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    categorie = models.CharField(max_length=20, choices=CategorieArticle.choices)
    unite = models.CharField(max_length=20)
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_articles"
        constraints = [
            models.UniqueConstraint(fields=["nom", "categorie"], name="uq_article_nom_categorie"),
        ]

    def __str__(self) -> str:
        return f"{self.nom} ({self.get_categorie_display()})"


class MouvementStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="mouvements")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type_mouvement = models.CharField(max_length=10, choices=TypeMouvement.choices)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=255, blank=True, null=True)
    reference_document = models.CharField(max_length=100, blank=True, null=True)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_mouvements"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantite__gt=0), name="chk_quantite_mouvement_positive")
        ]
        indexes = [models.Index(fields=["article", "date_mouvement"], name="idx_mouvements_article_date")]

    def __str__(self) -> str:
        return f"{self.get_type_mouvement_display()} {self.quantite} {self.article.unite} — {self.article.nom}"


class InventairePhysique(models.Model):
    """Inventaire physique hebdomadaire/mensuel avec écart calculé côté DB — §6."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="inventaires")
    date_inventaire = models.DateField()
    quantite_theorique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_physique = models.DecimalField(max_digits=10, decimal_places=2)
    ecart = models.GeneratedField(
        expression=F("quantite_physique") - F("quantite_theorique"),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )
    justification = models.TextField(blank=True, null=True)
    controle_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_inventaires_physiques"
        constraints = [
            models.UniqueConstraint(fields=["article", "date_inventaire"], name="uq_inventaire_article_date"),
        ]

    def __str__(self) -> str:
        return f"Inventaire {self.article.nom} — {self.date_inventaire}"
