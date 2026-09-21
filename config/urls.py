from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Les routes de chaque module (apps.elevage.urls, apps.stock.urls, ...)
    # seront incluses ici au fur et à mesure, ex:
    # path("api/elevage/", include("apps.elevage.urls")),
]
