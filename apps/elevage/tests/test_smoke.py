"""Test de fumée : vérifie que le projet démarre et que les modèles sont accessibles."""

import pytest

from apps.elevage.models import BandePondeuse, StatutBande


@pytest.mark.django_db
def test_creation_bande_pondeuse():
    bande = BandePondeuse.objects.create(
        nom="Bande A",
        date_mise_en_place="2026-01-01",
        effectif_initial=500,
        souche="ISA Brown",
    )
    assert bande.statut == StatutBande.ACTIVE
    assert BandePondeuse.objects.count() == 1
