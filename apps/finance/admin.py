from django.contrib import admin

from apps.finance.models import Depense


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ["date_depense", "categorie", "montant", "type_depense", "statut_approbation", "utilisateur"]
    list_filter = ["categorie", "type_depense", "statut_approbation"]
    date_hierarchy = "date_depense"
