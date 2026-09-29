from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    FermeShemaTokenObtainPairView,
    FermeShemaTokenRefreshView,
    LogoutView,
    UtilisateurViewSet,
)

router = DefaultRouter()
router.register("utilisateurs", UtilisateurViewSet, basename="utilisateur")

urlpatterns = [
    path("token/", FermeShemaTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", FermeShemaTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include(router.urls)),
]
