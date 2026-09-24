from django.db.models import Sum
from rest_framework import serializers

from apps.ventes.events import LigneVenteEvenement, VenteEnregistree
from apps.ventes.models import Client, LigneVente, Vente
from core.events import BusEvenements


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "nom", "type_client", "telephone", "limite_credit", "actif", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LigneVenteSerializer(serializers.ModelSerializer):
    montant_ligne = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = LigneVente
        fields = ["produit", "quantite", "prix_unitaire", "montant_ligne"]


class VenteSerializer(serializers.ModelSerializer):
    """
    Vente avec ses lignes créées en une seule requête (§7). Le montant_total
    n'est jamais fourni par le client : il est recalculé ici à partir des
    lignes, pour qu'il ne puisse jamais être incohérent avec le détail.

    Le contrôle de la limite de crédit (§7 : "les ventes à crédit devront
    respecter les limites fixées par le propriétaire") est fait avant toute
    écriture en base, jamais après coup.
    """

    solde = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    lignes = LigneVenteSerializer(many=True)

    class Meta:
        model = Vente
        fields = [
            "id",
            "client",
            "utilisateur",
            "date_vente",
            "mode_paiement",
            "montant_total",
            "montant_encaisse",
            "solde",
            "lignes",
            "created_at",
        ]
        read_only_fields = ["id", "utilisateur", "montant_total", "date_vente", "created_at"]

    def validate(self, attrs):
        if self.instance is None:
            lignes = attrs.get("lignes")
            if not lignes:
                raise serializers.ValidationError({"lignes": "Au moins une ligne de vente est requise."})
            montant_total = sum(ligne["quantite"] * ligne["prix_unitaire"] for ligne in lignes)
        else:
            montant_total = self.instance.montant_total

        montant_encaisse = attrs.get("montant_encaisse", getattr(self.instance, "montant_encaisse", 0))
        if montant_encaisse > montant_total:
            raise serializers.ValidationError(
                {"montant_encaisse": "Le montant encaissé ne peut pas dépasser le montant total."}
            )

        client = attrs.get("client", getattr(self.instance, "client", None))
        solde = montant_total - montant_encaisse
        if client and solde > 0:
            qs = Vente.objects.filter(client=client, solde__gt=0)
            if self.instance is not None:
                qs = qs.exclude(id=self.instance.id)
            credit_en_cours = qs.aggregate(total=Sum("solde"))["total"] or 0
            if credit_en_cours + solde > client.limite_credit:
                raise serializers.ValidationError(
                    {
                        "client": (
                            f"Limite de crédit dépassée : {credit_en_cours + solde} FCFA de créances "
                            f"cumulées pour une limite de {client.limite_credit} FCFA."
                        )
                    }
                )

        attrs["_montant_total_calcule"] = montant_total
        return attrs

    def create(self, validated_data):
        lignes_data = validated_data.pop("lignes")
        montant_total = validated_data.pop("_montant_total_calcule")
        validated_data["montant_total"] = montant_total
        validated_data["utilisateur"] = self.context["request"].user

        vente = Vente.objects.create(**validated_data)
        lignes = LigneVente.objects.bulk_create([LigneVente(vente=vente, **ligne) for ligne in lignes_data])

        BusEvenements.publier(
            VenteEnregistree(
                vente_id=vente.id,
                utilisateur_id=vente.utilisateur_id,
                client_id=vente.client_id,
                montant_total=float(vente.montant_total),
                lignes=[
                    LigneVenteEvenement(produit=ligne.produit, quantite=float(ligne.quantite)) for ligne in lignes
                ],
            )
        )
        return vente

    def update(self, instance, validated_data):
        # Une mise à jour (typiquement : enregistrer un encaissement, §14)
        # ne touche jamais aux lignes ni au montant_total déjà figés.
        validated_data.pop("lignes", None)
        validated_data.pop("_montant_total_calcule", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
