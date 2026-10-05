from django.contrib import admin

from apps.ventes.models import Client, LigneVente, Vente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0
    readonly_fields = ["montant_ligne"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["nom", "type_client", "limite_credit", "actif"]
    list_filter = ["type_client", "actif"]
    search_fields = ["nom", "telephone"]


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ["id", "client", "date_vente", "montant_total", "montant_encaisse", "solde", "mode_paiement"]
    list_filter = ["mode_paiement"]
    date_hierarchy = "date_vente"
    inlines = [LigneVenteInline]
