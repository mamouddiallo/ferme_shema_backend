from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stock"
    label = "stock"
    verbose_name = "Gestion des stocks"

    def ready(self):
        # Enregistre les abonnements aux événements des autres modules
        # (convention Django standard pour le code à exécuter au démarrage).
        from apps.stock import listeners  # noqa: F401
