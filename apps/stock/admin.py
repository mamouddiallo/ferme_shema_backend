from django.contrib import admin

from apps.stock.models import Article, InventairePhysique, MouvementStock


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["nom", "categorie", "unite", "seuil_alerte", "actif"]
    list_filter = ["categorie", "actif"]
    search_fields = ["nom"]


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ["article", "type_mouvement", "quantite", "date_mouvement", "utilisateur"]
    list_filter = ["type_mouvement", "article"]
    date_hierarchy = "date_mouvement"


@admin.register(InventairePhysique)
class InventairePhysiqueAdmin(admin.ModelAdmin):
    list_display = ["article", "date_inventaire", "quantite_theorique", "quantite_physique", "ecart"]
    list_filter = ["article"]
    date_hierarchy = "date_inventaire"
