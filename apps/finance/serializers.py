from rest_framework import serializers

from apps.finance.events import DepenseEnAttenteApprobation
from apps.finance.models import Depense, StatutApprobation, TypeDepense
from core.events import BusEvenements

# Types de dépense qui déclenchent obligatoirement un circuit d'approbation (§8)
TYPES_SOUMIS_A_APPROBATION = {TypeDepense.EXCEPTIONNELLE, TypeDepense.INVESTISSEMENT}


class DepenseSerializer(serializers.ModelSerializer):
    """
    Le statut d'approbation n'est jamais accepté en entrée : il est toujours
    dérivé du type de dépense, pour qu'il soit impossible de créer une
    dépense d'investissement en la faisant passer directement en
    'approuvee' depuis le client (§8).
    """

    class Meta:
        model = Depense
        fields = [
            "id",
            "utilisateur",
            "date_depense",
            "categorie",
            "montant",
            "type_depense",
            "justificatif_url",
            "statut_approbation",
            "approuve_par",
            "created_at",
        ]
        read_only_fields = ["id", "utilisateur", "statut_approbation", "approuve_par", "created_at"]

    def validate(self, attrs):
        type_depense = attrs.get("type_depense", getattr(self.instance, "type_depense", TypeDepense.COURANTE))
        justificatif_url = attrs.get("justificatif_url", getattr(self.instance, "justificatif_url", None))
        if type_depense == TypeDepense.INVESTISSEMENT and not justificatif_url:
            raise serializers.ValidationError(
                {"justificatif_url": "Un justificatif est obligatoire pour tout investissement (§8)."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["utilisateur"] = self.context["request"].user
        type_depense = validated_data.get("type_depense", TypeDepense.COURANTE)
        validated_data["statut_approbation"] = (
            StatutApprobation.EN_ATTENTE
            if type_depense in TYPES_SOUMIS_A_APPROBATION
            else StatutApprobation.NON_REQUISE
        )

        depense = super().create(validated_data)

        if depense.statut_approbation == StatutApprobation.EN_ATTENTE:
            BusEvenements.publier(
                DepenseEnAttenteApprobation(
                    depense_id=depense.id,
                    montant=float(depense.montant),
                    type_depense=depense.type_depense,
                    categorie=depense.categorie,
                )
            )
        return depense
