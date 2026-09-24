import logging

from core.events import abonne_a

logger = logging.getLogger("biosecurite.listeners")

# Au-delà de ce multiple du seuil normal, l'incident est classé critique
# plutôt que moyen (ex: seuil à 5% -> 2x = 10% déclenche 'critique').
MULTIPLICATEUR_GRAVITE_CRITIQUE = 2.0


@abonne_a("elevage.mortalite_anormale_detectee")
def creer_incident_depuis_mortalite_anormale(evenement) -> None:
    """
    Réagit à une mortalité anormale détectée par le module Élevage (§5) en
    créant automatiquement un incident sanitaire non résolu. Le module
    Biosécurité n'a besoin de rien connaître du module Élevage au-delà de ce
    que l'événement transporte.
    """
    # Import différé : évite tout risque de cycle d'import au chargement des
    # apps Django (biosecurite dépend d'elevage pour ses FK, pas l'inverse).
    from django.conf import settings

    from apps.biosecurite.models import IncidentSanitaire, NiveauGravite
    from apps.elevage.models import BandeChair, BandePondeuse

    seuil = settings.SEUIL_ALERTE_MORTALITE_PCT
    gravite = (
        NiveauGravite.CRITIQUE
        if evenement.taux_mortalite_pct >= seuil * MULTIPLICATEUR_GRAVITE_CRITIQUE
        else NiveauGravite.MOYENNE
    )

    description = (
        f"Mortalité anormale détectée automatiquement : {evenement.mortalite} morts sur "
        f"{evenement.effectif_debut} ({evenement.taux_mortalite_pct}%), seuil configuré à {seuil}%."
    )

    kwargs = {
        "date_incident": evenement.date_suivi,
        "description": description,
        "gravite": gravite,
        "resolu": False,
    }
    if evenement.type_bande == "pondeuse":
        kwargs["bande_pondeuse"] = BandePondeuse.objects.filter(id=evenement.bande_id).first()
    else:
        kwargs["bande_chair"] = BandeChair.objects.filter(id=evenement.bande_id).first()

    IncidentSanitaire.objects.create(**kwargs)
    logger.warning(
        "Incident sanitaire auto-créé : bande=%s taux=%.2f%%", evenement.bande_id, evenement.taux_mortalite_pct
    )
