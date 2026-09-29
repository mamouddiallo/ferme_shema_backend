from django.contrib import admin

from apps.elevage.models import BandeChair, BandePondeuse, SuiviChair, SuiviPondeuse


@admin.register(BandePondeuse)
class BandePondeuseAdmin(admin.ModelAdmin):
    list_display = ["nom", "date_mise_en_place", "effectif_initial", "statut"]
    list_filter = ["statut"]
    search_fields = ["nom", "souche"]


@admin.register(SuiviPondeuse)
class SuiviPondeuseAdmin(admin.ModelAdmin):
    list_display = ["bande", "date_suivi", "effectif_debut", "mortalite", "oeufs_produits", "stock_oeufs_restant"]
    list_filter = ["bande"]
    date_hierarchy = "date_suivi"


@admin.register(BandeChair)
class BandeChairAdmin(admin.ModelAdmin):
    list_display = ["nom", "date_arrivee", "effectif_initial", "statut", "chiffre_affaires"]
    list_filter = ["statut"]
    search_fields = ["nom", "souche"]


@admin.register(SuiviChair)
class SuiviChairAdmin(admin.ModelAdmin):
    list_display = ["bande", "date_suivi", "poids_moyen_g", "mortalite"]
    list_filter = ["bande"]
    date_hierarchy = "date_suivi"
