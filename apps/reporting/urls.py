from django.urls import path

from apps.reporting.views import RapportMensuelExportView, RapportMensuelView, TableauDeBordView

urlpatterns = [
    path("tableau-de-bord/", TableauDeBordView.as_view(), name="tableau-de-bord"),
    path("rapport-mensuel/", RapportMensuelView.as_view(), name="rapport-mensuel"),
    path("rapport-mensuel/export/", RapportMensuelExportView.as_view(), name="rapport-mensuel-export"),
]
