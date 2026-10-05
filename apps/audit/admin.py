from django.contrib import admin

from apps.audit.models import JournalAudit


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ["date_action", "action", "entite", "entite_id", "utilisateur"]
    list_filter = ["action", "entite"]
    date_hierarchy = "date_action"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
