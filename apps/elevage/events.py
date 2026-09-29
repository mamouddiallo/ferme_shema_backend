import uuid
from dataclasses import dataclass
from typing import ClassVar

from core.events import EvenementDomaine


@dataclass(frozen=True)
class BandeChairCloturee(EvenementDomaine):
    """
    Publié quand une bande de chair est vendue et clôturée. Le module
    Reporting pourra l'écouter pour ses agrégats sans que ce module ait
    besoin de le connaître.
    """

    nom: ClassVar[str] = "elevage.bande_chair_cloturee"
    bande_id: uuid.UUID = None
    nombre_vendu: int = 0
    chiffre_affaires: float = 0


@dataclass(frozen=True)
class MortaliteAnormaleDetectee(EvenementDomaine):
    """
    Publié quand la mortalité journalière d'une bande dépasse le seuil
    configuré (SEUIL_ALERTE_MORTALITE_PCT, §5). Le module Biosécurité
    l'écoute pour créer automatiquement un incident sanitaire, sans que ce
    module (Élevage) ait besoin de connaître son existence.
    """

    nom: ClassVar[str] = "elevage.mortalite_anormale_detectee"
    type_bande: str = ""  # "pondeuse" ou "chair"
    bande_id: uuid.UUID = None
    date_suivi: str = ""
    taux_mortalite_pct: float = 0
    mortalite: int = 0
    effectif_debut: int = 0
