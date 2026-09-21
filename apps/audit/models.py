import uuid

from django.conf import settings
from django.db import models


class JournalAudit(models.Model):
    """Journal transversal de traçabilité — prévention des pertes et fraudes (§12)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=50)  # ex: 'CREATE', 'UPDATE', 'DELETE'
    entite = models.CharField(max_length=100)  # ex: 'ventes.Vente'
    entite_id = models.UUIDField(blank=True, null=True)
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_journal"
        indexes = [
            models.Index(fields=["entite", "entite_id"], name="idx_audit_entite"),
            models.Index(fields=["date_action"], name="idx_audit_date"),
        ]

    def __str__(self) -> str:
        return f"{self.action} sur {self.entite} ({self.date_action:%Y-%m-%d %H:%M})"
