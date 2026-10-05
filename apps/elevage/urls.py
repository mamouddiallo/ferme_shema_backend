from rest_framework.routers import DefaultRouter

from apps.elevage.views import BandeChairViewSet, BandePondeuseViewSet, SuiviChairViewSet, SuiviPondeuseViewSet

router = DefaultRouter()
router.register("bandes-pondeuses", BandePondeuseViewSet, basename="bande-pondeuse")
router.register("suivi-pondeuse", SuiviPondeuseViewSet, basename="suivi-pondeuse")
router.register("bandes-chair", BandeChairViewSet, basename="bande-chair")
router.register("suivi-chair", SuiviChairViewSet, basename="suivi-chair")

urlpatterns = router.urls
