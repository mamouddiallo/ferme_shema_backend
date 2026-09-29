"""
Agrégations cross-module pour le reporting (§9, §10, §15). C'est le seul
endroit du projet où il est légitime de faire des requêtes directes sur
plusieurs apps métier à la fois — un module de reporting est par nature une
vue transverse, pas un domaine métier isolé.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.biosecurite.models import IncidentSanitaire
from apps.elevage.models import BandePondeuse, SuiviChair, SuiviPondeuse
from apps.finance.models import Depense
from apps.stock.models import MouvementStock
from apps.ventes.models import Vente


def _somme(queryset, champ) -> Decimal:
    return queryset.aggregate(total=Sum(champ))["total"] or Decimal("0")


def _stock_actuel_categorie(categorie: str) -> Decimal:
    entrees = _somme(MouvementStock.objects.filter(article__categorie=categorie, type_mouvement="entree"), "quantite")
    sorties = _somme(MouvementStock.objects.filter(article__categorie=categorie, type_mouvement="sortie"), "quantite")
    return entrees - sorties


def _effectif_poules_actuel() -> int:
    """Somme du dernier effectif connu (après mortalité du jour) de chaque bande active."""
    total = 0
    for bande in BandePondeuse.objects.filter(statut="active"):
        dernier_suivi = SuiviPondeuse.objects.filter(bande=bande).order_by("-date_suivi").first()
        if dernier_suivi:
            total += dernier_suivi.effectif_debut - dernier_suivi.mortalite
        else:
            total += bande.effectif_initial
    return total


def construire_tableau_de_bord(date_debut: date, date_fin: date) -> dict:
    """
    Reproduit le tableau de bord hebdomadaire du §9 : chaque indicateur sur
    la période demandée, plus le cumul du mois calendaire de date_fin.
    """
    debut_mois = date_fin.replace(day=1)
    fin_mois = date_fin.replace(day=calendar.monthrange(date_fin.year, date_fin.month)[1])

    def indicateurs(d_debut: date, d_fin: date) -> dict:
        suivis_pondeuse = SuiviPondeuse.objects.filter(date_suivi__range=(d_debut, d_fin))
        suivis_chair = SuiviChair.objects.filter(date_suivi__range=(d_debut, d_fin))
        ventes = Vente.objects.filter(date_vente__date__range=(d_debut, d_fin))
        depenses = Depense.objects.filter(date_depense__range=(d_debut, d_fin))

        oeufs_produits = _somme(suivis_pondeuse, "oeufs_produits")
        aliment_pondeuse = _somme(suivis_pondeuse, "aliment_distribue_kg")
        aliment_chair = _somme(suivis_chair, "aliment_distribue_kg")

        return {
            "oeufs_produits": oeufs_produits,
            "taux_ponte_moyen_pct": _taux_ponte_moyen(suivis_pondeuse),
            "oeufs_vendus": _somme(suivis_pondeuse, "oeufs_vendus"),
            "aliment_consomme_kg": aliment_pondeuse + aliment_chair,
            "mortalite": _somme(suivis_pondeuse, "mortalite") + _somme(suivis_chair, "mortalite"),
            "chiffre_affaires": _somme(ventes, "montant_total"),
            "depenses": _somme(depenses, "montant"),
            "encaissements": _somme(ventes, "montant_encaisse"),
        }

    return {
        "periode": {"debut": date_debut, "fin": date_fin},
        "semaine": indicateurs(date_debut, date_fin),
        "cumul_mensuel": indicateurs(debut_mois, fin_mois),
        "effectif_poules": _effectif_poules_actuel(),
        "creances_clients": _somme(Vente.objects.filter(solde__gt=0), "solde"),
        "stock_aliments_kg": _stock_actuel_categorie("aliment"),
        "incidents_non_resolus": IncidentSanitaire.objects.filter(resolu=False).count(),
    }


def _taux_ponte_moyen(suivis_pondeuse) -> Decimal:
    total_oeufs = _somme(suivis_pondeuse, "oeufs_produits")
    total_effectif = _somme(suivis_pondeuse, "effectif_debut")
    if total_effectif == 0:
        return Decimal("0")
    return round((total_oeufs / total_effectif) * 100, 2)


def construire_rapport_mensuel(mois: date) -> dict:
    """Compte d'exploitation du mois (§10) : reprend le calcul déjà utilisé en Finance."""
    debut_mois = mois.replace(day=1)
    fin_mois = mois.replace(day=calendar.monthrange(mois.year, mois.month)[1])

    ventes = Vente.objects.filter(date_vente__date__range=(debut_mois, fin_mois))
    depenses = Depense.objects.filter(date_depense__range=(debut_mois, fin_mois))

    depenses_par_categorie = {
        row["categorie"]: row["total"] for row in depenses.values("categorie").annotate(total=Sum("montant"))
    }

    chiffre_affaires = _somme(ventes, "montant_total")
    total_depenses = _somme(depenses, "montant")

    return {
        "mois": debut_mois,
        "chiffre_affaires": chiffre_affaires,
        "depenses_par_categorie": depenses_par_categorie,
        "total_depenses": total_depenses,
        "marge": chiffre_affaires - total_depenses,
        "nombre_ventes": ventes.count(),
    }


def semaine_par_defaut() -> tuple[date, date]:
    aujourdhui = date.today()
    return aujourdhui - timedelta(days=6), aujourdhui
