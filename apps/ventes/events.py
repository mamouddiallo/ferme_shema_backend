import uuid
from dataclasses import dataclass, field
from typing import ClassVar

from core.events import EvenementDomaine


@dataclass(frozen=True)
class LigneVenteEvenement:
    """Représentation minimale d'une ligne de vente pour le bus d'événements."""

    produit: str
    quantite: float


@dataclass(frozen=True)
class VenteEnregistree(EvenementDomaine):
    """
    Publié dès qu'une vente est confirmée. Le module Stock l'écoute pour
    décrémenter l'inventaire ; le module Reporting l'écoute pour ses KPI.
    Le module Ventes n'a besoin de connaître ni l'un ni l'autre.

    Ne transporte que des données simples (pas de FK vers un modèle Ventes) :
    c'est ce qui permet à Stock de réagir sans jamais importer apps.ventes.
    """

    nom: ClassVar[str] = "ventes.vente_enregistree"
    vente_id: uuid.UUID = None
    utilisateur_id: uuid.UUID = None
    client_id: uuid.UUID | None = None
    montant_total: float = 0
    lignes: list[LigneVenteEvenement] = field(default_factory=list)
