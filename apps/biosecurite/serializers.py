from rest_framework import serializers

from apps.biosecurite.models import IncidentSanitaire, InterventionVeterinaire


class _ValideBandeCibleMixin:
    """Vérifie qu'au moins une bande (pondeuse ou chair) est renseignée, avec un message clair."""

    def validate(self, attrs):
        bande_pondeuse = attrs.get("bande_pondeuse", getattr(self.instance, "bande_pondeuse", None))
        bande_chair = attrs.get("bande_chair", getattr(self.instance, "bande_chair", None))
        if not bande_pondeuse and not bande_chair:
            raise serializers.ValidationError(
                "Une intervention/incident doit concerner soit une bande de pondeuses, soit une bande de chair."
            )
        return attrs


class InterventionVeterinaireSerializer(_ValideBandeCibleMixin, serializers.ModelSerializer):
    class Meta:
        model = InterventionVeterinaire
        fields = [
            "id",
            "bande_pondeuse",
            "bande_chair",
            "date_intervention",
            "type_intervention",
            "produit",
            "dose",
            "observation",
            "cout",
            "saisi_par",
            "created_at",
        ]
        read_only_fields = ["id", "saisi_par", "created_at"]

    def create(self, validated_data):
        validated_data["saisi_par"] = self.context["request"].user
        return super().create(validated_data)


class IncidentSanitaireSerializer(_ValideBandeCibleMixin, serializers.ModelSerializer):
    class Meta:
        model = IncidentSanitaire
        fields = [
            "id",
            "bande_pondeuse",
            "bande_chair",
            "date_incident",
            "description",
            "gravite",
            "resolu",
            "signale_par",
            "created_at",
        ]
        read_only_fields = ["id", "signale_par", "created_at"]

    def create(self, validated_data):
        validated_data["signale_par"] = self.context["request"].user
        return super().create(validated_data)
