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
