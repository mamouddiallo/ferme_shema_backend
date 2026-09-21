# Ferme SHEMA — Backend

API de gestion de l'exploitation avicole. Django + Django REST Framework,
architecture en monolithe modulaire (un module = un bounded context métier).

## Structure

```
config/
  settings/       → base.py, dev.py, prod.py, test.py
  celery.py       → configuration du bus de tâches asynchrones
  urls.py
core/
  events.py       → bus d'événements interne (découplage entre modules)
apps/
  accounts/       → utilisateurs et rôles
  elevage/        → bandes pondeuses & poulets de chair
  biosecurite/    → registre vétérinaire, incidents sanitaires
  stock/          → articles, mouvements, inventaires
  ventes/         → clients, ventes
  finance/        → dépenses
  audit/          → journal de traçabilité
```

**Règle de modularité** : un module métier ne doit jamais importer les
modèles d'un autre module pour de la logique métier. La communication entre
modules passe par `core.events` (voir `apps/ventes/events.py` et
`apps/stock/listeners.py` pour un exemple concret).

## Démarrage rapide

```bash
cp .env.example .env      # puis ajuster les valeurs si besoin
make build
make up
make migrate
make superuser
```

L'API tourne alors sur http://localhost:8000, l'admin Django sur
http://localhost:8000/admin/.

## Commandes courantes

| Commande | Effet |
|---|---|
| `make test` | Lance la suite de tests (pytest) |
| `make lint` | Vérifie le style (Ruff) sans rien modifier |
| `make format` | Corrige automatiquement le style |
| `make shell` | Ouvre un shell Django dans le conteneur |
| `make logs` | Suit les logs du conteneur web |

## Qualité et CI

- **Ruff** fait office de linter + formatter (remplace flake8/isort/black en un seul outil).
- **pytest-django** pour les tests, avec couverture (`pytest-cov`).
- **pre-commit** exécute Ruff automatiquement avant chaque commit —
  installation : `pre-commit install` (une fois, en local, hors Docker).
- **GitHub Actions** (`.github/workflows/ci.yml`) relance lint + tests à
  chaque push/PR sur `main` et `develop`, avec de vrais services
  PostgreSQL et Redis.

## Documentation API

Générée automatiquement par `drf-spectacular` une fois les endpoints en
place, disponible sur `/api/schema/swagger-ui/`.
