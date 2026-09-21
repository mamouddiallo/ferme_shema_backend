import logging

from core.events import abonne_a

logger = logging.getLogger("stock.listeners")


@abonne_a("ventes.vente_enregistree")
def decrementer_stock_apres_vente(evenement) -> None:
    """
    Réagit à une vente confirmée. Ne connaît de la vente que ce que
    l'événement transporte (vente_id, montant_total) — aucun import du
    module ventes n'est nécessaire ici.
    """
    logger.info(
        "Vente %s enregistrée (%.2f) — vérification du stock associé à déclencher.",
        evenement.vente_id,
        evenement.montant_total,
    )
    # TODO: résoudre les lignes de vente -> articles concernés -> décrémenter
    # stock.models.Article via un mouvement de type 'sortie'.
