#!/usr/bin/env bash
# Génère la structure complète du backend Ferme SHEMA (Django + DRF + PostgreSQL).
# À exécuter depuis le terminal, DANS le dossier racine du repo cloné (vide).
set -e

echo "Création de la structure du projet backend..."

mkdir -p ".github"
mkdir -p ".github/workflows"
mkdir -p "apps"
mkdir -p "apps/accounts"
mkdir -p "apps/accounts/migrations"
mkdir -p "apps/audit"
mkdir -p "apps/audit/migrations"
mkdir -p "apps/biosecurite"
mkdir -p "apps/biosecurite/migrations"
mkdir -p "apps/elevage"
mkdir -p "apps/elevage/migrations"
mkdir -p "apps/elevage/tests"
mkdir -p "apps/finance"
mkdir -p "apps/finance/migrations"
mkdir -p "apps/stock"
mkdir -p "apps/stock/migrations"
mkdir -p "apps/ventes"
mkdir -p "apps/ventes/migrations"
mkdir -p "config"
mkdir -p "config/settings"
mkdir -p "core"
mkdir -p "requirements"

cat > ".dockerignore" << 'FERME_SHEMA_EOF_MARKER'
.git
.gitignore
.env
__pycache__
*.pyc
*.sqlite3
.venv
venv
.pytest_cache
.ruff_cache
htmlcov
.coverage
FERME_SHEMA_EOF_MARKER

cat > ".env.example" << 'FERME_SHEMA_EOF_MARKER'
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=ferme_shema_backend
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
FERME_SHEMA_EOF_MARKER

cat > ".github/workflows/ci.yml" << 'FERME_SHEMA_EOF_MARKER'
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Installer les dépendances de dev
        run: pip install -r requirements/dev.txt
      - name: Ruff (lint)
        run: ruff check .
      - name: Ruff (format check)
        run: ruff format --check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: ferme_shema_backend_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Installer les dépendances de dev
        run: pip install -r requirements/dev.txt
      - name: Vérification Django (system check)
        run: python manage.py check
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
      - name: Lancer les tests
        run: pytest
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          REDIS_URL: redis://localhost:6379/0
FERME_SHEMA_EOF_MARKER

cat > ".gitignore" << 'FERME_SHEMA_EOF_MARKER'
__pycache__/
*.py[cod]
*.sqlite3
.env
.venv/
venv/
staticfiles/
media/
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage
*.egg-info/
.DS_Store
FERME_SHEMA_EOF_MARKER

cat > ".pre-commit-config.yaml" << 'FERME_SHEMA_EOF_MARKER'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=1024]
FERME_SHEMA_EOF_MARKER

cat > "Dockerfile" << 'FERME_SHEMA_EOF_MARKER'
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système minimales pour psycopg (client PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

RUN python manage.py collectstatic --noinput --settings=config.settings.prod || true

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
FERME_SHEMA_EOF_MARKER

cat > "Makefile" << 'FERME_SHEMA_EOF_MARKER'
.PHONY: up down build migrate makemigrations shell test lint format logs

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

shell:
	docker compose exec web python manage.py shell

superuser:
	docker compose exec web python manage.py createsuperuser

test:
	docker compose exec web pytest

lint:
	docker compose exec web ruff check .
	docker compose exec web ruff format --check .

format:
	docker compose exec web ruff check --fix .
	docker compose exec web ruff format .

logs:
	docker compose logs -f web
FERME_SHEMA_EOF_MARKER

cat > "README.md" << 'FERME_SHEMA_EOF_MARKER'
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
FERME_SHEMA_EOF_MARKER

cat > "apps/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/accounts/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/accounts/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Utilisateurs et rôles"
FERME_SHEMA_EOF_MARKER

cat > "apps/accounts/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Utilisateur',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('role', models.CharField(choices=[('proprietaire', 'Propriétaire'), ('gestionnaire', 'Gestionnaire'), ('responsable_elevage', 'Responsable élevage'), ('ouvrier', 'Ouvrier'), ('comptable', 'Comptable')], max_length=30)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'utilisateurs',
                'indexes': [models.Index(fields=['role'], name='idx_utilisateurs_role')],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/accounts/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/accounts/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class RoleUtilisateur(models.TextChoices):
    PROPRIETAIRE = "proprietaire", "Propriétaire"
    GESTIONNAIRE = "gestionnaire", "Gestionnaire"
    RESPONSABLE_ELEVAGE = "responsable_elevage", "Responsable élevage"
    OUVRIER = "ouvrier", "Ouvrier"
    COMPTABLE = "comptable", "Comptable"


class Utilisateur(AbstractUser):
    """
    Étend AbstractUser plutôt que de repartir de zéro : on garde gratuitement
    username/email/password/is_active/last_login, et on ajoute le rôle métier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=RoleUtilisateur.choices)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "utilisateurs"
        indexes = [models.Index(fields=["role"], name="idx_utilisateurs_role")]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
FERME_SHEMA_EOF_MARKER

cat > "apps/audit/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/audit/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit & traçabilité"
FERME_SHEMA_EOF_MARKER

cat > "apps/audit/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JournalAudit',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=50)),
                ('entite', models.CharField(max_length=100)),
                ('entite_id', models.UUIDField(blank=True, null=True)),
                ('ancienne_valeur', models.JSONField(blank=True, null=True)),
                ('nouvelle_valeur', models.JSONField(blank=True, null=True)),
                ('date_action', models.DateTimeField(auto_now_add=True)),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'audit_journal',
                'indexes': [models.Index(fields=['entite', 'entite_id'], name='idx_audit_entite'), models.Index(fields=['date_action'], name='idx_audit_date')],
            },
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/audit/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/audit/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models


class JournalAudit(models.Model):
    """Journal transversal de traçabilité — prévention des pertes et fraudes (§12)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=50)  # ex: 'CREATE', 'UPDATE', 'DELETE'
    entite = models.CharField(max_length=100)  # ex: 'ventes.Vente'
    entite_id = models.UUIDField(blank=True, null=True)
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_journal"
        indexes = [
            models.Index(fields=["entite", "entite_id"], name="idx_audit_entite"),
            models.Index(fields=["date_action"], name="idx_audit_date"),
        ]

    def __str__(self) -> str:
        return f"{self.action} sur {self.entite} ({self.date_action:%Y-%m-%d %H:%M})"
FERME_SHEMA_EOF_MARKER

cat > "apps/biosecurite/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/biosecurite/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class BiosecuriteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.biosecurite"
    label = "biosecurite"
    verbose_name = "Biosécurité & santé animale"
FERME_SHEMA_EOF_MARKER

cat > "apps/biosecurite/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('elevage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IncidentSanitaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_incident', models.DateField()),
                ('description', models.TextField()),
                ('gravite', models.CharField(choices=[('faible', 'Faible'), ('moyenne', 'Moyenne'), ('critique', 'Critique')], default='moyenne', max_length=20)),
                ('resolu', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bande_chair', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='elevage.bandechair')),
                ('bande_pondeuse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='elevage.bandepondeuse')),
                ('signale_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'biosecurite_incidents_sanitaires',
                'indexes': [models.Index(fields=['resolu'], name='idx_incidents_resolu')],
                'constraints': [models.CheckConstraint(condition=models.Q(('bande_pondeuse__isnull', False), ('bande_chair__isnull', False), _connector='OR'), name='chk_bande_cible_incident')],
            },
        ),
        migrations.CreateModel(
            name='InterventionVeterinaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_intervention', models.DateField()),
                ('type_intervention', models.CharField(choices=[('vaccination', 'Vaccination'), ('traitement', 'Traitement'), ('visite_veterinaire', 'Visite vétérinaire')], max_length=30)),
                ('produit', models.CharField(blank=True, max_length=150, null=True)),
                ('dose', models.CharField(blank=True, max_length=100, null=True)),
                ('observation', models.TextField(blank=True, null=True)),
                ('cout', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bande_chair', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='elevage.bandechair')),
                ('bande_pondeuse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='elevage.bandepondeuse')),
                ('saisi_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'biosecurite_interventions_veterinaires',
                'indexes': [models.Index(fields=['date_intervention'], name='idx_interventions_date')],
                'constraints': [models.CheckConstraint(condition=models.Q(('bande_pondeuse__isnull', False), ('bande_chair__isnull', False), _connector='OR'), name='chk_bande_cible')],
            },
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/biosecurite/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/biosecurite/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models

from apps.elevage.models import BandeChair, BandePondeuse

_CHK_BANDE_CIBLE = models.Q(bande_pondeuse__isnull=False) | models.Q(bande_chair__isnull=False)


class TypeIntervention(models.TextChoices):
    VACCINATION = "vaccination", "Vaccination"
    TRAITEMENT = "traitement", "Traitement"
    VISITE_VETERINAIRE = "visite_veterinaire", "Visite vétérinaire"


class NiveauGravite(models.TextChoices):
    FAIBLE = "faible", "Faible"
    MOYENNE = "moyenne", "Moyenne"
    CRITIQUE = "critique", "Critique"


class InterventionVeterinaire(models.Model):
    """Registre vétérinaire (vaccinations, traitements, visites) — §5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande_pondeuse = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, blank=True, null=True)
    bande_chair = models.ForeignKey(BandeChair, on_delete=models.CASCADE, blank=True, null=True)
    date_intervention = models.DateField()
    type_intervention = models.CharField(max_length=30, choices=TypeIntervention.choices)
    produit = models.CharField(max_length=150, blank=True, null=True)
    dose = models.CharField(max_length=100, blank=True, null=True)
    observation = models.TextField(blank=True, null=True)
    cout = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "biosecurite_interventions_veterinaires"
        constraints = [models.CheckConstraint(condition=_CHK_BANDE_CIBLE, name="chk_bande_cible")]
        indexes = [models.Index(fields=["date_intervention"], name="idx_interventions_date")]

    def __str__(self) -> str:
        cible = self.bande_pondeuse or self.bande_chair
        return f"{self.get_type_intervention_display()} — {cible} ({self.date_intervention})"


class IncidentSanitaire(models.Model):
    """Signalement immédiat de mortalité inhabituelle ou suspicion de maladie — §5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande_pondeuse = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, blank=True, null=True)
    bande_chair = models.ForeignKey(BandeChair, on_delete=models.CASCADE, blank=True, null=True)
    date_incident = models.DateField()
    description = models.TextField()
    gravite = models.CharField(max_length=20, choices=NiveauGravite.choices, default=NiveauGravite.MOYENNE)
    resolu = models.BooleanField(default=False)
    signale_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "biosecurite_incidents_sanitaires"
        constraints = [models.CheckConstraint(condition=_CHK_BANDE_CIBLE, name="chk_bande_cible_incident")]
        indexes = [models.Index(fields=["resolu"], name="idx_incidents_resolu")]

    def __str__(self) -> str:
        cible = self.bande_pondeuse or self.bande_chair
        return f"Incident {self.get_gravite_display()} — {cible} ({self.date_incident})"
FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class ElevageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.elevage"
    label = "elevage"
    verbose_name = "Élevage (pondeuses & poulets de chair)"
FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BandeChair',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=100)),
                ('date_arrivee', models.DateField()),
                ('effectif_initial', models.PositiveIntegerField()),
                ('souche', models.CharField(blank=True, max_length=100, null=True)),
                ('poids_initial_g', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('statut', models.CharField(choices=[('active', 'Active'), ('terminee', 'Terminée'), ('suspendue', 'Suspendue')], default='active', max_length=20)),
                ('date_vente', models.DateField(blank=True, null=True)),
                ('nombre_vendu', models.PositiveIntegerField(blank=True, null=True)),
                ('poids_vendu_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('chiffre_affaires', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'elevage_bandes_chair',
                'constraints': [models.CheckConstraint(condition=models.Q(('effectif_initial__gt', 0)), name='chk_effectif_initial_chair_positif')],
            },
        ),
        migrations.CreateModel(
            name='BandePondeuse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=100)),
                ('date_mise_en_place', models.DateField()),
                ('effectif_initial', models.PositiveIntegerField()),
                ('souche', models.CharField(blank=True, max_length=100, null=True)),
                ('statut', models.CharField(choices=[('active', 'Active'), ('terminee', 'Terminée'), ('suspendue', 'Suspendue')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'elevage_bandes_pondeuses',
                'constraints': [models.CheckConstraint(condition=models.Q(('effectif_initial__gt', 0)), name='chk_effectif_initial_positif')],
            },
        ),
        migrations.CreateModel(
            name='SuiviChair',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_suivi', models.DateField()),
                ('poids_moyen_g', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('aliment_distribue_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('mortalite', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suivis', to='elevage.bandechair')),
                ('saisi_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'elevage_suivi_chair',
                'constraints': [models.UniqueConstraint(fields=('bande', 'date_suivi'), name='uq_suivi_chair_bande_date')],
            },
        ),
        migrations.CreateModel(
            name='SuiviPondeuse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_suivi', models.DateField()),
                ('effectif_debut', models.PositiveIntegerField()),
                ('mortalite', models.PositiveIntegerField(default=0)),
                ('aliment_distribue_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('eau_consommee_l', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('oeufs_produits', models.PositiveIntegerField(default=0)),
                ('oeufs_casses', models.PositiveIntegerField(default=0)),
                ('oeufs_vendus', models.PositiveIntegerField(default=0)),
                ('stock_oeufs_restant', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suivis', to='elevage.bandepondeuse')),
                ('saisi_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'elevage_suivi_pondeuse',
                'indexes': [models.Index(fields=['bande', 'date_suivi'], name='idx_suivi_pondeuse_bande_date')],
                'constraints': [models.UniqueConstraint(fields=('bande', 'date_suivi'), name='uq_suivi_pondeuse_bande_date')],
            },
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models


class StatutBande(models.TextChoices):
    ACTIVE = "active", "Active"
    TERMINEE = "terminee", "Terminée"
    SUSPENDUE = "suspendue", "Suspendue"


class BandePondeuse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    date_mise_en_place = models.DateField()
    effectif_initial = models.PositiveIntegerField()
    souche = models.CharField(max_length=100, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=StatutBande.choices, default=StatutBande.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elevage_bandes_pondeuses"
        constraints = [
            models.CheckConstraint(condition=models.Q(effectif_initial__gt=0), name="chk_effectif_initial_positif"),
        ]

    def __str__(self) -> str:
        return self.nom


class SuiviPondeuse(models.Model):
    """Registre journalier d'une bande de pondeuses — champs minimum imposés au §4."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande = models.ForeignKey(BandePondeuse, on_delete=models.CASCADE, related_name="suivis")
    date_suivi = models.DateField()
    effectif_debut = models.PositiveIntegerField()
    mortalite = models.PositiveIntegerField(default=0)
    aliment_distribue_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    eau_consommee_l = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    oeufs_produits = models.PositiveIntegerField(default=0)
    oeufs_casses = models.PositiveIntegerField(default=0)
    oeufs_vendus = models.PositiveIntegerField(default=0)
    stock_oeufs_restant = models.PositiveIntegerField(default=0)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elevage_suivi_pondeuse"
        constraints = [
            models.UniqueConstraint(fields=["bande", "date_suivi"], name="uq_suivi_pondeuse_bande_date"),
        ]
        indexes = [models.Index(fields=["bande", "date_suivi"], name="idx_suivi_pondeuse_bande_date")]

    def __str__(self) -> str:
        return f"{self.bande.nom} — {self.date_suivi}"


class BandeChair(models.Model):
    """Fiche de bande de poulets de chair — inclut les infos de clôture/vente (§4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    date_arrivee = models.DateField()
    effectif_initial = models.PositiveIntegerField()
    souche = models.CharField(max_length=100, blank=True, null=True)
    poids_initial_g = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=StatutBande.choices, default=StatutBande.ACTIVE)
    # Clôture de bande, renseignée à la vente
    date_vente = models.DateField(blank=True, null=True)
    nombre_vendu = models.PositiveIntegerField(blank=True, null=True)
    poids_vendu_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    chiffre_affaires = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elevage_bandes_chair"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(effectif_initial__gt=0), name="chk_effectif_initial_chair_positif"
            ),
        ]

    def __str__(self) -> str:
        return self.nom


class SuiviChair(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bande = models.ForeignKey(BandeChair, on_delete=models.CASCADE, related_name="suivis")
    date_suivi = models.DateField()
    poids_moyen_g = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    aliment_distribue_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    mortalite = models.PositiveIntegerField(default=0)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elevage_suivi_chair"
        constraints = [
            models.UniqueConstraint(fields=["bande", "date_suivi"], name="uq_suivi_chair_bande_date"),
        ]

    def __str__(self) -> str:
        return f"{self.bande.nom} — {self.date_suivi}"
FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/tests/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/elevage/tests/test_smoke.py" << 'FERME_SHEMA_EOF_MARKER'
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
FERME_SHEMA_EOF_MARKER

cat > "apps/finance/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/finance/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = "Gestion financière"
FERME_SHEMA_EOF_MARKER

cat > "apps/finance/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Depense',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_depense', models.DateField()),
                ('categorie', models.CharField(choices=[('aliment', 'Aliment'), ('medicament_soins', 'Médicaments & soins'), ('salaires', 'Salaires'), ('eau_electricite', 'Eau & électricité'), ('transport', 'Transport'), ('entretien', 'Entretien'), ('emballage', 'Emballage'), ('autre', 'Autre')], max_length=30)),
                ('montant', models.DecimalField(decimal_places=2, max_digits=12)),
                ('type_depense', models.CharField(choices=[('courante', 'Courante'), ('exceptionnelle', 'Exceptionnelle'), ('investissement', 'Investissement')], default='courante', max_length=20)),
                ('justificatif_url', models.URLField(blank=True, max_length=500, null=True)),
                ('statut_approbation', models.CharField(choices=[('en_attente', 'En attente'), ('approuvee', 'Approuvée'), ('rejetee', 'Rejetée'), ('non_requise', 'Non requise')], default='non_requise', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approuve_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='depenses_approuvees', to=settings.AUTH_USER_MODEL)),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='depenses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'finance_depenses',
                'indexes': [models.Index(fields=['date_depense'], name='idx_depenses_date'), models.Index(fields=['categorie'], name='idx_depenses_categorie')],
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('type_depense', 'investissement'), _negated=True), ('justificatif_url__isnull', False), _connector='OR'), name='chk_justificatif_investissement')],
            },
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/finance/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/finance/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models


class TypeDepense(models.TextChoices):
    COURANTE = "courante", "Courante"
    EXCEPTIONNELLE = "exceptionnelle", "Exceptionnelle"
    INVESTISSEMENT = "investissement", "Investissement"


class StatutApprobation(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    APPROUVEE = "approuvee", "Approuvée"
    REJETEE = "rejetee", "Rejetée"
    NON_REQUISE = "non_requise", "Non requise"


class CategorieDepense(models.TextChoices):
    ALIMENT = "aliment", "Aliment"
    MEDICAMENT_SOINS = "medicament_soins", "Médicaments & soins"
    SALAIRES = "salaires", "Salaires"
    EAU_ELECTRICITE = "eau_electricite", "Eau & électricité"
    TRANSPORT = "transport", "Transport"
    ENTRETIEN = "entretien", "Entretien"
    EMBALLAGE = "emballage", "Emballage"
    AUTRE = "autre", "Autre"


class Depense(models.Model):
    """Dépenses avec workflow d'approbation selon le type — §8."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="depenses")
    date_depense = models.DateField()
    categorie = models.CharField(max_length=30, choices=CategorieDepense.choices)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_depense = models.CharField(max_length=20, choices=TypeDepense.choices, default=TypeDepense.COURANTE)
    justificatif_url = models.URLField(max_length=500, blank=True, null=True)
    statut_approbation = models.CharField(
        max_length=20, choices=StatutApprobation.choices, default=StatutApprobation.NON_REQUISE
    )
    approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="depenses_approuvees"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_depenses"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(type_depense=TypeDepense.INVESTISSEMENT)
                | models.Q(justificatif_url__isnull=False),
                name="chk_justificatif_investissement",
            ),
        ]
        indexes = [
            models.Index(fields=["date_depense"], name="idx_depenses_date"),
            models.Index(fields=["categorie"], name="idx_depenses_categorie"),
        ]

    def __str__(self) -> str:
        return f"{self.get_categorie_display()} — {self.montant} ({self.date_depense})"
FERME_SHEMA_EOF_MARKER

cat > "apps/stock/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/stock/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stock"
    label = "stock"
    verbose_name = "Gestion des stocks"

    def ready(self):
        # Enregistre les abonnements aux événements des autres modules
        # (convention Django standard pour le code à exécuter au démarrage).
        from apps.stock import listeners  # noqa: F401
FERME_SHEMA_EOF_MARKER

cat > "apps/stock/listeners.py" << 'FERME_SHEMA_EOF_MARKER'
import logging

from core.events import abonne_a

logger = logging.getLogger("stock.listeners")


@abonne_a("ventes.vente_enregistree")
def decrementer_stock_apres_vente(evenement) -> None:
    """
    Réagit à une vente confirmée. Ne connaît de la vente que ce que
    l'événement transporte (vente_id, montant_total) — aucun import du
    module ventes n'est nécessaire ici.
    """
    logger.info(
        "Vente %s enregistrée (%.2f) — vérification du stock associé à déclencher.",
        evenement.vente_id,
        evenement.montant_total,
    )
    # TODO: résoudre les lignes de vente -> articles concernés -> décrémenter
    # stock.models.Article via un mouvement de type 'sortie'.
FERME_SHEMA_EOF_MARKER

cat > "apps/stock/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import django.db.models.expressions
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=150)),
                ('categorie', models.CharField(choices=[('aliment', 'Aliment'), ('medicament', 'Médicament'), ('vaccin', 'Vaccin'), ('desinfectant', 'Désinfectant'), ('emballage', 'Emballage'), ('plateau_oeufs', "Plateau d'œufs"), ('materiel', 'Matériel'), ('piece_rechange', 'Pièce de rechange'), ('autre', 'Autre')], max_length=20)),
                ('unite', models.CharField(max_length=20)),
                ('seuil_alerte', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('actif', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'stock_articles',
                'constraints': [models.UniqueConstraint(fields=('nom', 'categorie'), name='uq_article_nom_categorie')],
            },
        ),
        migrations.CreateModel(
            name='InventairePhysique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_inventaire', models.DateField()),
                ('quantite_theorique', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantite_physique', models.DecimalField(decimal_places=2, max_digits=10)),
                ('ecart', models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(models.F('quantite_physique'), '-', models.F('quantite_theorique')), output_field=models.DecimalField(decimal_places=2, max_digits=10))),
                ('justification', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inventaires', to='stock.article')),
                ('controle_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'stock_inventaires_physiques',
                'constraints': [models.UniqueConstraint(fields=('article', 'date_inventaire'), name='uq_inventaire_article_date')],
            },
        ),
        migrations.CreateModel(
            name='MouvementStock',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type_mouvement', models.CharField(choices=[('entree', 'Entrée'), ('sortie', 'Sortie')], max_length=10)),
                ('quantite', models.DecimalField(decimal_places=2, max_digits=10)),
                ('motif', models.CharField(blank=True, max_length=255, null=True)),
                ('reference_document', models.CharField(blank=True, max_length=100, null=True)),
                ('date_mouvement', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mouvements', to='stock.article')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'stock_mouvements',
                'indexes': [models.Index(fields=['article', 'date_mouvement'], name='idx_mouvements_article_date')],
                'constraints': [models.CheckConstraint(condition=models.Q(('quantite__gt', 0)), name='chk_quantite_mouvement_positive')],
            },
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/stock/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/stock/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


class CategorieArticle(models.TextChoices):
    ALIMENT = "aliment", "Aliment"
    MEDICAMENT = "medicament", "Médicament"
    VACCIN = "vaccin", "Vaccin"
    DESINFECTANT = "desinfectant", "Désinfectant"
    EMBALLAGE = "emballage", "Emballage"
    PLATEAU_OEUFS = "plateau_oeufs", "Plateau d'œufs"
    MATERIEL = "materiel", "Matériel"
    PIECE_RECHANGE = "piece_rechange", "Pièce de rechange"
    AUTRE = "autre", "Autre"


class TypeMouvement(models.TextChoices):
    ENTREE = "entree", "Entrée"
    SORTIE = "sortie", "Sortie"


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    categorie = models.CharField(max_length=20, choices=CategorieArticle.choices)
    unite = models.CharField(max_length=20)
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_articles"
        constraints = [
            models.UniqueConstraint(fields=["nom", "categorie"], name="uq_article_nom_categorie"),
        ]

    def __str__(self) -> str:
        return f"{self.nom} ({self.get_categorie_display()})"


class MouvementStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="mouvements")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type_mouvement = models.CharField(max_length=10, choices=TypeMouvement.choices)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=255, blank=True, null=True)
    reference_document = models.CharField(max_length=100, blank=True, null=True)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_mouvements"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantite__gt=0), name="chk_quantite_mouvement_positive")
        ]
        indexes = [models.Index(fields=["article", "date_mouvement"], name="idx_mouvements_article_date")]

    def __str__(self) -> str:
        return f"{self.get_type_mouvement_display()} {self.quantite} {self.article.unite} — {self.article.nom}"


class InventairePhysique(models.Model):
    """Inventaire physique hebdomadaire/mensuel avec écart calculé côté DB — §6."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="inventaires")
    date_inventaire = models.DateField()
    quantite_theorique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_physique = models.DecimalField(max_digits=10, decimal_places=2)
    ecart = models.GeneratedField(
        expression=F("quantite_physique") - F("quantite_theorique"),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )
    justification = models.TextField(blank=True, null=True)
    controle_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_inventaires_physiques"
        constraints = [
            models.UniqueConstraint(fields=["article", "date_inventaire"], name="uq_inventaire_article_date"),
        ]

    def __str__(self) -> str:
        return f"Inventaire {self.article.nom} — {self.date_inventaire}"
FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/apps.py" << 'FERME_SHEMA_EOF_MARKER'
from django.apps import AppConfig


class VentesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ventes"
    label = "ventes"
    verbose_name = "Ventes & clients"
FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/events.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid
from dataclasses import dataclass
from typing import ClassVar

from core.events import EvenementDomaine


@dataclass(frozen=True)
class VenteEnregistree(EvenementDomaine):
    """
    Publié dès qu'une vente est confirmée. Le module Stock l'écoute pour
    décrémenter l'inventaire ; le module Reporting l'écoute pour ses KPI.
    Le module Ventes n'a besoin de connaître ni l'un ni l'autre.
    """

    nom: ClassVar[str] = "ventes.vente_enregistree"
    vente_id: uuid.UUID = None
    client_id: uuid.UUID | None = None
    montant_total: float = 0
FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/migrations/0001_initial.py" << 'FERME_SHEMA_EOF_MARKER'
# Generated by Django 6.1.1 on 2026-09-16 15:24

import django.db.models.deletion
import django.db.models.expressions
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=150)),
                ('type_client', models.CharField(choices=[('particulier', 'Particulier'), ('restaurant', 'Restaurant'), ('hotel', 'Hôtel'), ('supermarche', 'Supermarché'), ('revendeur', 'Revendeur'), ('boulangerie', 'Boulangerie'), ('autre', 'Autre')], max_length=20)),
                ('telephone', models.CharField(blank=True, max_length=30, null=True)),
                ('limite_credit', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('actif', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ventes_clients',
            },
        ),
        migrations.CreateModel(
            name='Vente',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_vente', models.DateTimeField(auto_now_add=True)),
                ('mode_paiement', models.CharField(choices=[('especes', 'Espèces'), ('mobile_money', 'Mobile money'), ('virement', 'Virement'), ('cheque', 'Chèque'), ('credit', 'Crédit')], max_length=20)),
                ('montant_total', models.DecimalField(decimal_places=2, max_digits=12)),
                ('montant_encaisse', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('solde', models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(models.F('montant_total'), '-', models.F('montant_encaisse')), output_field=models.DecimalField(decimal_places=2, max_digits=12))),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ventes', to='ventes.client')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ventes_ventes',
            },
        ),
        migrations.CreateModel(
            name='LigneVente',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('produit', models.CharField(max_length=150)),
                ('quantite', models.DecimalField(decimal_places=2, max_digits=10)),
                ('prix_unitaire', models.DecimalField(decimal_places=2, max_digits=10)),
                ('montant_ligne', models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(models.F('quantite'), '*', models.F('prix_unitaire')), output_field=models.DecimalField(decimal_places=2, max_digits=12))),
                ('vente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes', to='ventes.vente')),
            ],
            options={
                'db_table': 'ventes_lignes',
            },
        ),
        migrations.AddIndex(
            model_name='vente',
            index=models.Index(fields=['client', 'date_vente'], name='idx_ventes_client_date'),
        ),
        migrations.AddConstraint(
            model_name='vente',
            constraint=models.CheckConstraint(condition=models.Q(('montant_encaisse__lte', models.F('montant_total'))), name='chk_encaisse_inferieur_total'),
        ),
    ]
FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/migrations/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "apps/ventes/models.py" << 'FERME_SHEMA_EOF_MARKER'
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


class TypeClient(models.TextChoices):
    PARTICULIER = "particulier", "Particulier"
    RESTAURANT = "restaurant", "Restaurant"
    HOTEL = "hotel", "Hôtel"
    SUPERMARCHE = "supermarche", "Supermarché"
    REVENDEUR = "revendeur", "Revendeur"
    BOULANGERIE = "boulangerie", "Boulangerie"
    AUTRE = "autre", "Autre"


class ModePaiement(models.TextChoices):
    ESPECES = "especes", "Espèces"
    MOBILE_MONEY = "mobile_money", "Mobile money"
    VIREMENT = "virement", "Virement"
    CHEQUE = "cheque", "Chèque"
    CREDIT = "credit", "Crédit"


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    type_client = models.CharField(max_length=20, choices=TypeClient.choices)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    limite_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ventes_clients"

    def __str__(self) -> str:
        return self.nom


class Vente(models.Model):
    """En-tête de vente — date, client, paiement, montants (§7)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="ventes", blank=True, null=True)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_vente = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    montant_encaisse = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    solde = models.GeneratedField(
        expression=F("montant_total") - F("montant_encaisse"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ventes_ventes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(montant_encaisse__lte=F("montant_total")),
                name="chk_encaisse_inferieur_total",
            ),
        ]
        indexes = [models.Index(fields=["client", "date_vente"], name="idx_ventes_client_date")]

    def __str__(self) -> str:
        return f"Vente {self.id} — {self.montant_total} ({self.date_vente:%Y-%m-%d})"


class LigneVente(models.Model):
    """Détail produit/quantité/prix d'une vente (normalisé par rapport au MCD initial)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name="lignes")
    produit = models.CharField(max_length=150)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ligne = models.GeneratedField(
        expression=F("quantite") * F("prix_unitaire"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )

    class Meta:
        db_table = "ventes_lignes"

    def __str__(self) -> str:
        return f"{self.quantite} x {self.produit}"
FERME_SHEMA_EOF_MARKER

cat > "config/__init__.py" << 'FERME_SHEMA_EOF_MARKER'
# S'assure que l'app Celery est chargée dès le démarrage de Django,
# pour que @shared_task fonctionne dans tous les modules.
from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
FERME_SHEMA_EOF_MARKER

cat > "config/asgi.py" << 'FERME_SHEMA_EOF_MARKER'
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_asgi_application()
FERME_SHEMA_EOF_MARKER

cat > "config/celery.py" << 'FERME_SHEMA_EOF_MARKER'
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("ferme_shema_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Requête de tâche de test : {self.request!r}")
FERME_SHEMA_EOF_MARKER

cat > "config/settings/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "config/settings/base.py" << 'FERME_SHEMA_EOF_MARKER'
"""
Settings communs à tous les environnements.
Ne jamais mettre de valeur de secret en dur ici — tout passe par des variables
d'environnement (voir .env.example à la racine).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_celery_results",
    # Modules métier — un module = un bounded context (§ architecture)
    "apps.accounts",
    "apps.elevage",
    "apps.biosecurite",
    "apps.stock",
    "apps.ventes",
    "apps.finance",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Modèle utilisateur personnalisé avec rôles métier (§14 de l'organigramme)
AUTH_USER_MODEL = "accounts.Utilisateur"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "ferme_shema_backend"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # connexions persistantes, utile en charge
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Ferme SHEMA",
    "DESCRIPTION": "API de gestion de l'exploitation avicole (élevage, stock, ventes, finance, biosécurité).",
    "VERSION": "1.0.0",
}

# --- Celery : bus de tâches asynchrones (rapports, notifications, KPI lourds) ---
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# --- Cache Redis (KPI calculés, rate limiting) ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    }
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
FERME_SHEMA_EOF_MARKER

cat > "config/settings/dev.py" << 'FERME_SHEMA_EOF_MARKER'
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

# En dev, les erreurs Celery ne doivent jamais bloquer une requête HTTP
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true"  # noqa: F405
FERME_SHEMA_EOF_MARKER

cat > "config/settings/prod.py" << 'FERME_SHEMA_EOF_MARKER'
from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")  # noqa: F405

if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS doit être défini en production.")

if SECRET_KEY == "insecure-dev-key-change-me":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY doit être défini explicitement en production.")

# Durcissement sécurité, essentiel dès qu'on est exposé sur internet
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
FERME_SHEMA_EOF_MARKER

cat > "config/settings/test.py" << 'FERME_SHEMA_EOF_MARKER'
from .base import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True  # les tâches Celery s'exécutent en synchrone pendant les tests

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # hash rapide, tests uniquement
FERME_SHEMA_EOF_MARKER

cat > "config/urls.py" << 'FERME_SHEMA_EOF_MARKER'
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Les routes de chaque module (apps.elevage.urls, apps.stock.urls, ...)
    # seront incluses ici au fur et à mesure, ex:
    # path("api/elevage/", include("apps.elevage.urls")),
]
FERME_SHEMA_EOF_MARKER

cat > "config/wsgi.py" << 'FERME_SHEMA_EOF_MARKER'
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
FERME_SHEMA_EOF_MARKER

cat > "core/__init__.py" << 'FERME_SHEMA_EOF_MARKER'

FERME_SHEMA_EOF_MARKER

cat > "core/events.py" << 'FERME_SHEMA_EOF_MARKER'
"""
Bus d'événements interne au monolithe modulaire.

Principe : un module publie un événement métier (ex: VenteEnregistree) sans
savoir qui l'écoute. D'autres modules s'abonnent à cet événement sans importer
le module émetteur. Ça garantit qu'aucun module ne dépend directement d'un
autre — condition nécessaire pour pouvoir un jour extraire un module en
microservice indépendant sans tout réécrire.

Implémentation actuelle : dispatch synchrone en mémoire (suffisant pour un
monolithe mono-instance). Le jour où on a besoin de fiabilité (ne jamais
perdre un événement même si le process crash), on route `publish()` vers une
tâche Celery qui persiste puis dispatch — sans changer l'API pour les modules
appelants.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

logger = logging.getLogger("evenements")


@dataclass(frozen=True)
class EvenementDomaine:
    """Classe de base de tout événement métier publié sur le bus."""

    nom: ClassVar[str] = "evenement.generique"
    horodatage: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BusEvenements:
    _abonnes: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    @classmethod
    def abonner(cls, nom_evenement: str, gestionnaire: Callable[[Any], None]) -> None:
        cls._abonnes[nom_evenement].append(gestionnaire)
        logger.debug("Abonnement enregistré: %s -> %s", nom_evenement, gestionnaire.__qualname__)

    @classmethod
    def publier(cls, evenement: EvenementDomaine) -> None:
        gestionnaires = cls._abonnes.get(evenement.nom, [])
        logger.info("Événement publié: %s (%d abonné(s))", evenement.nom, len(gestionnaires))
        for gestionnaire in gestionnaires:
            try:
                gestionnaire(evenement)
            except Exception:  # un abonné qui échoue ne doit jamais faire échouer l'émetteur
                logger.exception("Échec du gestionnaire %s pour %s", gestionnaire.__qualname__, evenement.nom)


def abonne_a(nom_evenement: str):
    """Décorateur pour enregistrer une fonction comme abonnée à un événement."""

    def decorateur(fonction):
        BusEvenements.abonner(nom_evenement, fonction)
        return fonction

    return decorateur
FERME_SHEMA_EOF_MARKER

cat > "docker-compose.yml" << 'FERME_SHEMA_EOF_MARKER'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-ferme_shema_backend}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.dev
      DB_HOST: db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_worker:
    build: .
    command: celery -A config worker --loglevel=info
    volumes:
      - .:/app
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.dev
      DB_HOST: db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
FERME_SHEMA_EOF_MARKER

cat > "manage.py" << 'FERME_SHEMA_EOF_MARKER'
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez qu'il est installé et "
            "disponible dans votre variable d'environnement PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
FERME_SHEMA_EOF_MARKER

cat > "pyproject.toml" << 'FERME_SHEMA_EOF_MARKER'
[tool.black]
line-length = 119
target-version = ["py312"]

[tool.ruff]
line-length = 119
target-version = "py312"
exclude = ["*/migrations/*"]

[tool.ruff.lint]
select = ["E", "F", "I", "DJ", "B"]  # pyflakes, pycodestyle, isort, django, bugbear
ignore = ["DJ001"]  # null=True sur CharField : on l'utilise volontairement pour distinguer "vide" de "non renseigné"

[tool.ruff.lint.isort]
known-first-party = ["apps", "config", "core"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py", "*_test.py"]
addopts = "--reuse-db --cov=apps --cov=core --cov-report=term-missing"
FERME_SHEMA_EOF_MARKER

cat > "requirements/base.txt" << 'FERME_SHEMA_EOF_MARKER'
Django>=5.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
drf-spectacular>=0.27
psycopg[binary]>=3.1
python-dotenv>=1.0
celery>=5.4
django-celery-results>=2.5
redis>=5.0
gunicorn>=22.0
FERME_SHEMA_EOF_MARKER

cat > "requirements/dev.txt" << 'FERME_SHEMA_EOF_MARKER'
-r base.txt

django-extensions>=3.2
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
factory-boy>=3.3
ruff>=0.6
black>=24.0
pre-commit>=3.7
FERME_SHEMA_EOF_MARKER

cat > "requirements/prod.txt" << 'FERME_SHEMA_EOF_MARKER'
-r base.txt

sentry-sdk>=2.0
FERME_SHEMA_EOF_MARKER

echo "Structure créée avec succès."
echo "Fichiers créés : 66"
echo ""
echo "Prochaine étape :"
echo "  git add ."
echo "  git commit -m \"Structure initiale + outillage (Docker, Celery, CI, settings par environnement)\""
echo "  git push -u origin main"
