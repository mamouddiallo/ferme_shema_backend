from django.db.models import Sum
from rest_framework import serializers

from apps.elevage.models import BandeChair, BandePondeuse, StatutBande, SuiviChair, SuiviPondeuse


class BandePondeuseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BandePondeuse
        fields = ["id", "nom", "date_mise_en_place", "effectif_initial", "souche", "statut", "created_at"]
        read_only_fields = ["id", "created_at"]


class SuiviPondeuseSerializer(serializers.ModelSerializer):
    """
    Registre journalier (§4). Deux règles métier sont vérifiées ici plutôt
    que laissées à la seule contrainte UNIQUE de la base :
    - la mortalité ne peut pas dépasser l'effectif du jour ;
    - on ne peut pas vendre/casser plus d'œufs que ce qui est réellement
      disponible (production du jour + stock restant de la veille).

    `stock_oeufs_restant` est calculé ici, jamais fourni par le client — ça
    évite qu'un chiffre incohérent soit saisi par erreur.
    """

    stock_oeufs_restant = serializers.IntegerField(read_only=True)

    class Meta:
        model = SuiviPondeuse
        fields = [
            "id",
            "bande",
            "date_suivi",
            "effectif_debut",
            "mortalite",
            "aliment_distribue_kg",
            "eau_consommee_l",
            "oeufs_produits",
            "oeufs_casses",
            "oeufs_vendus",
            "stock_oeufs_restant",
            "saisi_par",
            "created_at",
        ]
        read_only_fields = ["id", "saisi_par", "created_at"]

    def _stock_veille(self, bande, date_suivi, exclude_id=None):
        qs = SuiviPondeuse.objects.filter(bande=bande, date_suivi__lt=date_suivi).order_by("-date_suivi")
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        dernier = qs.first()
        return dernier.stock_oeufs_restant if dernier else 0

    def validate(self, attrs):
        effectif_debut = attrs.get("effectif_debut", getattr(self.instance, "effectif_debut", None))
        mortalite = attrs.get("mortalite", getattr(self.instance, "mortalite", 0))
        if mortalite > effectif_debut:
            raise serializers.ValidationError(
                {"mortalite": "La mortalité ne peut pas dépasser l'effectif du début de journée."}
            )

        bande = attrs.get("bande", getattr(self.instance, "bande", None))
        date_suivi = attrs.get("date_suivi", getattr(self.instance, "date_suivi", None))
        oeufs_produits = attrs.get("oeufs_produits", getattr(self.instance, "oeufs_produits", 0))
        oeufs_casses = attrs.get("oeufs_casses", getattr(self.instance, "oeufs_casses", 0))
        oeufs_vendus = attrs.get("oeufs_vendus", getattr(self.instance, "oeufs_vendus", 0))

        stock_veille = self._stock_veille(bande, date_suivi, exclude_id=getattr(self.instance, "id", None))
        disponible = oeufs_produits + stock_veille
        if oeufs_casses + oeufs_vendus > disponible:
            raise serializers.ValidationError(
                {
                    "oeufs_vendus": (
                        f"Impossible de vendre/casser {oeufs_casses + oeufs_vendus} œufs : "
                        f"seulement {disponible} disponibles (production du jour + stock de la veille)."
                    )
                }
            )

        attrs["stock_oeufs_restant"] = disponible - oeufs_casses - oeufs_vendus
        return attrs

    def create(self, validated_data):
        validated_data["saisi_par"] = self.context["request"].user
        return super().create(validated_data)


class BandeChairSerializer(serializers.ModelSerializer):
    class Meta:
        model = BandeChair
        fields = [
            "id",
            "nom",
            "date_arrivee",
            "effectif_initial",
            "souche",
            "poids_initial_g",
            "statut",
            "date_vente",
            "nombre_vendu",
            "poids_vendu_kg",
            "chiffre_affaires",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "statut",
            "date_vente",
            "nombre_vendu",
            "poids_vendu_kg",
            "chiffre_affaires",
            "created_at",
            "updated_at",
        ]


class ClotureBandeChairSerializer(serializers.Serializer):
    """Champs acceptés uniquement par l'action de clôture (E5), pas par le CRUD standard."""

    date_vente = serializers.DateField()
    nombre_vendu = serializers.IntegerField(min_value=1)
    poids_vendu_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    chiffre_affaires = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    def validate(self, attrs):
        bande = self.context["bande"]
        if bande.statut != StatutBande.ACTIVE:
            raise serializers.ValidationError("Seule une bande active peut être clôturée.")
        if attrs["nombre_vendu"] > bande.effectif_initial:
            raise serializers.ValidationError(
                {"nombre_vendu": "Le nombre vendu ne peut pas dépasser l'effectif initial de la bande."}
            )
        return attrs


class SuiviChairSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuiviChair
        fields = [
            "id",
            "bande",
            "date_suivi",
            "poids_moyen_g",
            "aliment_distribue_kg",
            "mortalite",
            "saisi_par",
            "created_at",
        ]
        read_only_fields = ["id", "saisi_par", "created_at"]

    def validate(self, attrs):
        bande = attrs.get("bande", getattr(self.instance, "bande", None))
        mortalite = attrs.get("mortalite", 0)
        # Mortalité cumulée du suivi ne doit pas dépasser l'effectif initial de la bande
        cumul_existant = (
            SuiviChair.objects.filter(bande=bande)
            .exclude(id=getattr(self.instance, "id", None))
            .aggregate(total=Sum("mortalite"))["total"]
            or 0
        )
        if cumul_existant + mortalite > bande.effectif_initial:
            raise serializers.ValidationError(
                {"mortalite": "La mortalité cumulée dépasserait l'effectif initial de la bande."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["saisi_par"] = self.context["request"].user
        return super().create(validated_data)
