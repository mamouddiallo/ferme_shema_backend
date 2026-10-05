from rest_framework import serializers

from apps.stock.models import Article, InventairePhysique, MouvementStock


class ArticleSerializer(serializers.ModelSerializer):
    stock_actuel = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "nom", "categorie", "unite", "seuil_alerte", "actif", "stock_actuel", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_stock_actuel(self, obj) -> float:
        from django.db.models import Sum

        entrees = obj.mouvements.filter(type_mouvement="entree").aggregate(total=Sum("quantite"))["total"] or 0
        sorties = obj.mouvements.filter(type_mouvement="sortie").aggregate(total=Sum("quantite"))["total"] or 0
        return float(entrees) - float(sorties)


class MouvementStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MouvementStock
        fields = [
            "id",
            "article",
            "utilisateur",
            "type_mouvement",
            "quantite",
            "motif",
            "reference_document",
            "date_mouvement",
            "created_at",
        ]
        read_only_fields = ["id", "utilisateur", "date_mouvement", "created_at"]

    def create(self, validated_data):
        validated_data["utilisateur"] = self.context["request"].user
        return super().create(validated_data)


class InventairePhysiqueSerializer(serializers.ModelSerializer):
    """
    Inventaire physique (§6). L'écart lui-même est calculé par PostgreSQL
    (colonne générée) — ici on vérifie seulement la règle métier : tout
    écart doit être expliqué.
    """

    ecart = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = InventairePhysique
        fields = [
            "id",
            "article",
            "date_inventaire",
            "quantite_theorique",
            "quantite_physique",
            "ecart",
            "justification",
            "controle_par",
            "created_at",
        ]
        read_only_fields = ["id", "ecart", "controle_par", "created_at"]

    def validate(self, attrs):
        theorique = attrs.get("quantite_theorique", getattr(self.instance, "quantite_theorique", None))
        physique = attrs.get("quantite_physique", getattr(self.instance, "quantite_physique", None))
        justification = attrs.get("justification", getattr(self.instance, "justification", None))
        if theorique != physique and not justification:
            raise serializers.ValidationError(
                {"justification": "Un écart entre stock théorique et physique doit être justifié (§6)."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["controle_par"] = self.context["request"].user
        return super().create(validated_data)
