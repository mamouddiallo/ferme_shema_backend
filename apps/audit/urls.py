from rest_framework.routers import DefaultRouter

from apps.audit.views import JournalAuditViewSet

router = DefaultRouter()
router.register("journal", JournalAuditViewSet, basename="journal-audit")

urlpatterns = router.urls
