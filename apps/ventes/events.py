import uuid
from dataclasses import dataclass
from typing import ClassVar

from core.events import EvenementDomaine


@dataclass(frozen=True)
class VenteEnregistree(EvenementDomaine):
    """
    Publié dès qu'une vente est confirmée. Le module Stock l'écoute pour
    décrémenter l'inventaire ; le module Reporting l'écoute pour ses KPI.
    Le module Ventes n'a besoin de connaître ni l'un ni l'autre.
    """

    nom: ClassVar[str] = "ventes.vente_enregistree"
    vente_id: uuid.UUID = None
    client_id: uuid.UUID | None = None
    montant_total: float = 0
