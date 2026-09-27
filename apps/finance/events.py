import uuid
from dataclasses import dataclass
from typing import ClassVar

from core.events import EvenementDomaine


@dataclass(frozen=True)
class DepenseEnAttenteApprobation(EvenementDomaine):
    """
    Publié quand une dépense exceptionnelle ou un investissement est créé et
    nécessite l'accord du propriétaire (§8). Un futur module de
    notification (email/SMS) pourra s'y abonner sans que ce module ait
    besoin de le connaître.
    """

    nom: ClassVar[str] = "finance.depense_en_attente_approbation"
    depense_id: uuid.UUID = None
    montant: float = 0
    type_depense: str = ""
    categorie: str = ""


@dataclass(frozen=True)
class DepenseApprouvee(EvenementDomaine):
    nom: ClassVar[str] = "finance.depense_approuvee"
    depense_id: uuid.UUID = None
    approuve_par_id: uuid.UUID = None


@dataclass(frozen=True)
class DepenseRejetee(EvenementDomaine):
    nom: ClassVar[str] = "finance.depense_rejetee"
    depense_id: uuid.UUID = None
    rejete_par_id: uuid.UUID = None
