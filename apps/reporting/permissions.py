from apps.accounts.permissions import EstComptableOuPlus

# Réutilise directement la permission existante (proprietaire, gestionnaire,
# comptable) : le reporting agrège des données financières, la même
# sensibilité s'applique qu'au module Finance.
PeutConsulterReporting = EstComptableOuPlus
