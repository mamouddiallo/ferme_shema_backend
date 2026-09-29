from rest_framework.routers import DefaultRouter

from apps.ventes.views import ClientViewSet, VenteViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("ventes", VenteViewSet, basename="vente")

urlpatterns = router.urls
