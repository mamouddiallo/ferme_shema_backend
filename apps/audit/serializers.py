from rest_framework import serializers

from apps.audit.models import JournalAudit


class JournalAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalAudit
        fields = [
            "id",
            "utilisateur",
            "action",
            "entite",
            "entite_id",
            "ancienne_valeur",
            "nouvelle_valeur",
            "date_action",
        ]
        read_only_fields = fields
