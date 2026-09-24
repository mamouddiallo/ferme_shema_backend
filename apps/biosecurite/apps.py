from django.apps import AppConfig


class BiosecuriteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.biosecurite"
    label = "biosecurite"
    verbose_name = "Biosécurité & santé animale"

    def ready(self):
        from apps.biosecurite import listeners  # noqa: F401
