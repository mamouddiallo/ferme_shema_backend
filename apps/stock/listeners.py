import logging

from core.events import abonne_a

logger = logging.getLogger("stock.listeners")


@abonne_a("ventes.vente_enregistree")
def decrementer_stock_apres_vente(evenement) -> None:
    """
    Réagit à une vente confirmée en créant un mouvement de sortie de stock
    pour chaque ligne vendue. Ne connaît de la vente que ce que l'événement
    transporte — aucun import du module ventes n'est nécessaire ici.

    La correspondance produit -> article se fait par nom (insensible à la
    casse) : c'est la seule information partagée entre les deux modules,
    volontairement, pour ne pas créer de FK cross-module.
    """
    # Import différé : évite tout risque de cycle au chargement des apps.
    from apps.accounts.models import Utilisateur
    from apps.stock.models import Article, MouvementStock, TypeMouvement

    utilisateur = None
    if evenement.utilisateur_id:
        utilisateur = Utilisateur.objects.filter(id=evenement.utilisateur_id).first()

    if utilisateur is None:
        logger.error(
            "Vente %s : utilisateur introuvable (id=%s) — mouvements de stock ignorés.",
            evenement.vente_id,
            evenement.utilisateur_id,
        )
        return

    for ligne in evenement.lignes:
        article = Article.objects.filter(nom__iexact=ligne.produit, actif=True).first()
        if article is None:
            logger.warning(
                "Vente %s : aucun article de stock ne correspond à '%s' — mouvement ignoré.",
                evenement.vente_id,
                ligne.produit,
            )
            continue

        MouvementStock.objects.create(
            article=article,
            utilisateur=utilisateur,
            type_mouvement=TypeMouvement.SORTIE,
            quantite=ligne.quantite,
            motif=f"Vente {evenement.vente_id}",
            reference_document=str(evenement.vente_id),
        )
        logger.info(
            "Stock décrémenté : %s -%.2f %s (vente %s)",
            article.nom,
            ligne.quantite,
            article.unite,
            evenement.vente_id,
        )
