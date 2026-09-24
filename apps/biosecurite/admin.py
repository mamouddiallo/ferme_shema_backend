from django.contrib import admin

from apps.biosecurite.models import IncidentSanitaire, InterventionVeterinaire


@admin.register(InterventionVeterinaire)
class InterventionVeterinaireAdmin(admin.ModelAdmin):
    list_display = ["date_intervention", "type_intervention", "bande_pondeuse", "bande_chair", "cout"]
    list_filter = ["type_intervention"]
    date_hierarchy = "date_intervention"


@admin.register(IncidentSanitaire)
class IncidentSanitaireAdmin(admin.ModelAdmin):
    list_display = ["date_incident", "gravite", "resolu", "bande_pondeuse", "bande_chair"]
    list_filter = ["gravite", "resolu"]
    date_hierarchy = "date_incident"
