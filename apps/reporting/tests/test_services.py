"""
Tests de apps.reporting.services — la logique d'agrégation elle-même,
indépendamment des vues/permissions. On construit des données réalistes sur
plusieurs modules et on vérifie que les totaux sont exacts.
"""

from datetime import date

import pytest

from apps.accounts.models import RoleUtilisateur, Utilisateur
from apps.biosecurite.models import IncidentSanitaire
from apps.elevage.models import BandePondeuse, SuiviPondeuse
from apps.finance.models import Depense
from apps.reporting.services import construire_rapport_mensuel, construire_tableau_de_bord
from apps.stock.models import Article, CategorieArticle, MouvementStock
from apps.ventes.models import Client, TypeClient, Vente


@pytest.fixture
def gestionnaire(db):
    return Utilisateur.objects.create_user(
        username="gest1", email="g@test.local", password="pass12345", role=RoleUtilisateur.GESTIONNAIRE
    )


@pytest.mark.django_db
class TestTableauDeBord:
    def test_agrege_correctement_plusieurs_modules(self, gestionnaire):
        bande = BandePondeuse.objects.create(
            nom="Bande A", date_mise_en_place="2026-01-01", effectif_initial=500, souche="ISA Brown"
        )
        SuiviPondeuse.objects.create(
            bande=bande,
            date_suivi=date(2026, 9, 22),
            effectif_debut=498,
            mortalite=1,
            oeufs_produits=430,
            oeufs_vendus=400,
            aliment_distribue_kg=50,
            saisi_par=gestionnaire,
        )

        client = Client.objects.create(nom="Client X", type_client=TypeClient.PARTICULIER, limite_credit=0)
        Vente.objects.create(
            client=client,
            utilisateur=gestionnaire,
            date_vente="2026-09-22T10:00:00Z",
            mode_paiement="especes",
            montant_total=45000,
            montant_encaisse=30000,
        )
        Depense.objects.create(
            utilisateur=gestionnaire,
            date_depense="2026-09-22",
            categorie="aliment",
            montant=20000,
            type_depense="courante",
        )

        tableau = construire_tableau_de_bord(date(2026, 9, 22), date(2026, 9, 22))

        assert tableau["semaine"]["oeufs_produits"] == 430
        assert tableau["semaine"]["oeufs_vendus"] == 400
        assert float(tableau["semaine"]["taux_ponte_moyen_pct"]) == pytest.approx(86.35, rel=0.01)
        assert float(tableau["semaine"]["chiffre_affaires"]) == 45000.0
        assert float(tableau["semaine"]["depenses"]) == 20000.0
        assert float(tableau["semaine"]["encaissements"]) == 30000.0
        assert float(tableau["creances_clients"]) == 15000.0  # 45000 - 30000

    def test_effectif_poules_deduit_la_mortalite_du_dernier_suivi(self, gestionnaire):
        bande = BandePondeuse.objects.create(
            nom="Bande B", date_mise_en_place="2026-01-01", effectif_initial=500, souche="ISA Brown"
        )
        SuiviPondeuse.objects.create(
            bande=bande, date_suivi=date(2026, 9, 20), effectif_debut=500, mortalite=2, oeufs_produits=430
        )
        SuiviPondeuse.objects.create(
            bande=bande, date_suivi=date(2026, 9, 21), effectif_debut=498, mortalite=3, oeufs_produits=420
        )
        tableau = construire_tableau_de_bord(date(2026, 9, 21), date(2026, 9, 21))
        # Dernier suivi (21/09) : effectif_debut=498, mortalite=3 -> 495 poules restantes
        assert tableau["effectif_poules"] == 495

    def test_stock_aliments_reflete_les_mouvements(self, gestionnaire):
        article = Article.objects.create(
            nom="Aliment ponte", categorie=CategorieArticle.ALIMENT, unite="kg", seuil_alerte=100
        )
        MouvementStock.objects.create(article=article, utilisateur=gestionnaire, type_mouvement="entree", quantite=500)
        MouvementStock.objects.create(article=article, utilisateur=gestionnaire, type_mouvement="sortie", quantite=120)
        tableau = construire_tableau_de_bord(date(2026, 9, 22), date(2026, 9, 22))
        assert float(tableau["stock_aliments_kg"]) == 380.0

    def test_incidents_non_resolus_est_compte(self, gestionnaire):
        bande = BandePondeuse.objects.create(nom="Bande C", date_mise_en_place="2026-01-01", effectif_initial=500)
        IncidentSanitaire.objects.create(
            bande_pondeuse=bande, date_incident="2026-09-20", description="Test", resolu=False
        )
        IncidentSanitaire.objects.create(
            bande_pondeuse=bande, date_incident="2026-09-20", description="Résolu", resolu=True
        )
        tableau = construire_tableau_de_bord(date(2026, 9, 22), date(2026, 9, 22))
        assert tableau["incidents_non_resolus"] == 1

    def test_cumul_mensuel_inclut_toute_les_donnees_du_mois(self, gestionnaire):
        bande = BandePondeuse.objects.create(nom="Bande D", date_mise_en_place="2026-01-01", effectif_initial=500)
        SuiviPondeuse.objects.create(bande=bande, date_suivi=date(2026, 9, 5), effectif_debut=500, oeufs_produits=400)
        SuiviPondeuse.objects.create(bande=bande, date_suivi=date(2026, 9, 25), effectif_debut=498, oeufs_produits=420)
        # La semaine ne couvre que le 25, mais le cumul mensuel doit inclure le 5 aussi
        tableau = construire_tableau_de_bord(date(2026, 9, 25), date(2026, 9, 25))
        assert tableau["semaine"]["oeufs_produits"] == 420
        assert tableau["cumul_mensuel"]["oeufs_produits"] == 820


@pytest.mark.django_db
class TestRapportMensuel:
    def test_calcule_la_marge_et_le_detail_par_categorie(self, gestionnaire):
        client = Client.objects.create(nom="Client Y", type_client=TypeClient.PARTICULIER, limite_credit=0)
        Vente.objects.create(
            client=client,
            utilisateur=gestionnaire,
            date_vente="2026-09-10T10:00:00Z",
            mode_paiement="especes",
            montant_total=100000,
            montant_encaisse=100000,
        )
        Depense.objects.create(utilisateur=gestionnaire, date_depense="2026-09-05", categorie="aliment", montant=30000)
        Depense.objects.create(
            utilisateur=gestionnaire, date_depense="2026-09-15", categorie="transport", montant=10000
        )

        rapport = construire_rapport_mensuel(date(2026, 9, 1))

        assert float(rapport["chiffre_affaires"]) == 100000.0
        assert float(rapport["total_depenses"]) == 40000.0
        assert float(rapport["marge"]) == 60000.0
        assert float(rapport["depenses_par_categorie"]["aliment"]) == 30000.0
        assert float(rapport["depenses_par_categorie"]["transport"]) == 10000.0
        assert rapport["nombre_ventes"] == 1

    def test_mois_sans_activite_renvoie_des_zeros_pas_une_erreur(self):
        rapport = construire_rapport_mensuel(date(2020, 1, 1))
        assert float(rapport["chiffre_affaires"]) == 0.0
        assert float(rapport["marge"]) == 0.0
