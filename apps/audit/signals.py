"""
Journalisation automatique des modèles sensibles (§12 : prévention des
pertes et fraudes). Générique : connecter_audit(Modele1, Modele2, ...)
suffit à faire suivre n'importe quel modèle, sans dupliquer de code.
"""

import json

from django.db.models.signals import post_delete, post_save, pre_save
from django.forms.models import model_to_dict

from apps.audit.threadlocal import get_current_user

# Champs jamais journalisés, quel que soit le modèle (secrets, données volumineuses)
CHAMPS_EXCLUS = {"password", "mot_de_passe_hash"}


def _json_safe(valeur):
    """Convertit Decimal/UUID/date/etc. en types sérialisables JSON."""
    return json.loads(json.dumps(valeur, default=str))


def _serialiser(instance) -> dict:
    donnees = model_to_dict(instance)
    donnees = {cle: valeur for cle, valeur in donnees.items() if cle not in CHAMPS_EXCLUS}
    return _json_safe(donnees)


def _audit_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._etat_avant_audit = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._etat_avant_audit = None
    else:
        instance._etat_avant_audit = None


def _audit_post_save(sender, instance, created, **kwargs):
    from apps.audit.models import JournalAudit

    etat_avant = getattr(instance, "_etat_avant_audit", None)
    JournalAudit.objects.create(
        utilisateur=get_current_user(),
        action="CREATE" if created else "UPDATE",
        entite=f"{sender._meta.app_label}.{sender.__name__}",
        entite_id=instance.pk,
        ancienne_valeur=_serialiser(etat_avant) if etat_avant else None,
        nouvelle_valeur=_serialiser(instance),
    )


def _audit_post_delete(sender, instance, **kwargs):
    from apps.audit.models import JournalAudit

    JournalAudit.objects.create(
        utilisateur=get_current_user(),
        action="DELETE",
        entite=f"{sender._meta.app_label}.{sender.__name__}",
        entite_id=instance.pk,
        ancienne_valeur=_serialiser(instance),
        nouvelle_valeur=None,
    )


def connecter_audit(*modeles) -> None:
    for modele in modeles:
        pre_save.connect(_audit_pre_save, sender=modele, weak=False)
        post_save.connect(_audit_post_save, sender=modele, weak=False)
        post_delete.connect(_audit_post_delete, sender=modele, weak=False)
