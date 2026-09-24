from rest_framework.routers import DefaultRouter

from apps.stock.views import ArticleViewSet, InventairePhysiqueViewSet, MouvementStockViewSet

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("mouvements", MouvementStockViewSet, basename="mouvement-stock")
router.register("inventaires", InventairePhysiqueViewSet, basename="inventaire-physique")

urlpatterns = router.urls
