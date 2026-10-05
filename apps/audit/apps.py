from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit & traçabilité"

    def ready(self):
        from apps.audit.signals import connecter_audit
        from apps.finance.models import Depense
        from apps.stock.models import InventairePhysique, MouvementStock
        from apps.ventes.models import Vente

        # Modèles sensibles du §12 : argent et stock, le cœur de la prévention
        # de fraude. D'autres modèles pourront être ajoutés ici plus tard.
        connecter_audit(Vente, Depense, MouvementStock, InventairePhysique)
