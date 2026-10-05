from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    """
    Endpoint public, sans authentification (vue Django brute, pas DRF —
    elle ignore donc complètement DEFAULT_PERMISSION_CLASSES). Sert de
    sonde de santé pour Render/tout orchestrateur : doit toujours répondre
    200 tant que l'application et sa connexion DB fonctionnent.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/elevage/", include("apps.elevage.urls")),
    path("api/biosecurite/", include("apps.biosecurite.urls")),
    path("api/stock/", include("apps.stock.urls")),
    path("api/ventes/", include("apps.ventes.urls")),
    path("api/finance/", include("apps.finance.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/reporting/", include("apps.reporting.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
