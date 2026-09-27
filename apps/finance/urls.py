from rest_framework.routers import DefaultRouter

from apps.finance.views import DepenseViewSet

router = DefaultRouter()
router.register("depenses", DepenseViewSet, basename="depense")

urlpatterns = router.urls
