from rest_framework.routers import DefaultRouter

from apps.biosecurite.views import IncidentSanitaireViewSet, InterventionVeterinaireViewSet

router = DefaultRouter()
router.register("interventions", InterventionVeterinaireViewSet, basename="intervention-veterinaire")
router.register("incidents", IncidentSanitaireViewSet, basename="incident-sanitaire")

urlpatterns = router.urls
