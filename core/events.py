"""
Bus d'événements interne au monolithe modulaire.

Principe : un module publie un événement métier (ex: VenteEnregistree) sans
savoir qui l'écoute. D'autres modules s'abonnent à cet événement sans importer
le module émetteur. Ça garantit qu'aucun module ne dépend directement d'un
autre — condition nécessaire pour pouvoir un jour extraire un module en
microservice indépendant sans tout réécrire.

Implémentation actuelle : dispatch synchrone en mémoire (suffisant pour un
monolithe mono-instance). Le jour où on a besoin de fiabilité (ne jamais
perdre un événement même si le process crash), on route `publish()` vers une
tâche Celery qui persiste puis dispatch — sans changer l'API pour les modules
appelants.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

logger = logging.getLogger("evenements")


@dataclass(frozen=True)
class EvenementDomaine:
    """Classe de base de tout événement métier publié sur le bus."""

    nom: ClassVar[str] = "evenement.generique"
    horodatage: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BusEvenements:
    _abonnes: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    @classmethod
    def abonner(cls, nom_evenement: str, gestionnaire: Callable[[Any], None]) -> None:
        cls._abonnes[nom_evenement].append(gestionnaire)
        logger.debug("Abonnement enregistré: %s -> %s", nom_evenement, gestionnaire.__qualname__)

    @classmethod
    def publier(cls, evenement: EvenementDomaine) -> None:
        gestionnaires = cls._abonnes.get(evenement.nom, [])
        logger.info("Événement publié: %s (%d abonné(s))", evenement.nom, len(gestionnaires))
        for gestionnaire in gestionnaires:
            try:
                gestionnaire(evenement)
            except Exception:  # un abonné qui échoue ne doit jamais faire échouer l'émetteur
                logger.exception("Échec du gestionnaire %s pour %s", gestionnaire.__qualname__, evenement.nom)


def abonne_a(nom_evenement: str):
    """Décorateur pour enregistrer une fonction comme abonnée à un événement."""

    def decorateur(fonction):
        BusEvenements.abonner(nom_evenement, fonction)
        return fonction

    return decorateur
