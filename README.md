# Ferme SHEMA — Backend

API REST de gestion d'une exploitation avicole : élevage (poules pondeuses et
poulets de chair), biosécurité, stock, ventes, finance, audit et reporting.

**Stack** : Python 3.12 · Django 6 · Django REST Framework · PostgreSQL 16 ·
Redis · authentification JWT.

---

## 1. Prérequis

| Outil | Version | Vérification |
|---|---|---|
| Git | récent | `git --version` |
| Python | 3.12 ou plus | `python3 --version` |
| Docker + Docker Compose v2 | récent | `docker --version` puis `docker compose version` |

Le projet a été développé et testé sous **Linux (Ubuntu)**. Sous Windows,
utilisez de préférence WSL2 ; Docker Desktop exige que la virtualisation soit
activée dans le BIOS.

---

## 2. Installation pas à pas

### 2.1 Récupérer le code

```bash
git clone https://github.com/mamouddiallo/ferme_shema_backend.git
cd ferme_shema_backend
git checkout develop
```

### 2.2 Créer l'environnement Python

```bash
python3 -m venv venv
source venv/bin/activate        # Windows (PowerShell) : venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements/dev.txt
```

Le préfixe `(venv)` doit apparaître dans votre terminal. Il faudra réactiver
l'environnement (`source venv/bin/activate`) à chaque nouvelle session.

### 2.3 Créer le fichier de configuration

```bash
cp .env.example .env
```

Le fichier `.env` n'est jamais versionné. Remplacez la clé secrète par une
vraie valeur :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copiez le résultat dans `.env`, sur la ligne `DJANGO_SECRET_KEY=`. Avec la
valeur par défaut `change-me`, tout fonctionne mais les tests affichent un
avertissement sur la longueur de la clé.

### 2.4 Démarrer PostgreSQL et Redis

```bash
docker compose up -d db redis
docker compose ps
```

> **Ne lancez pas `docker compose up` sans préciser `db redis`.** Le fichier
> définit aussi d'autres services (`web`, `celery_worker`) qui entreraient en
> conflit avec le serveur lancé à l'étape 2.7.

Dans la sortie de `docker compose ps`, vérifiez :

- les services `db` et `redis` sont en statut **healthy** (quelques secondes
  après le démarrage) ;
- la colonne `PORTS` de `db` indique le port exposé sur votre machine, par
  exemple `0.0.0.0:5433->5432/tcp`. **Cette valeur doit être identique à
  `DB_PORT` dans votre `.env`.** Le fichier `.env.example` est préconfiguré
  pour `5433`, afin d'éviter un conflit avec un PostgreSQL déjà installé sur
  votre machine (qui occupe en général le port 5432).

Redis est **indispensable même en développement** : la limitation du nombre de
tentatives de connexion s'appuie dessus, et sans lui les requêtes restent
bloquées sans réponse.

### 2.5 Créer les tables

```bash
python manage.py migrate
```

Vous devez voir défiler une liste de lignes `Applying ... OK`.

### 2.6 Créer votre compte propriétaire

```bash
python manage.py createsuperuser
```

Ce compte reçoit automatiquement le rôle **propriétaire**, le plus élevé de
l'application (voir la section 5).

### 2.7 Lancer le serveur

```bash
python manage.py runserver
```

Laissez ce terminal ouvert : le serveur s'arrête si vous le fermez. Ouvrez un
second terminal pour les autres commandes.

### 2.8 Vérifier que tout fonctionne

```bash
curl http://localhost:8000/health/
```

Réponse attendue : `{"status": "ok"}`. Elle prouve que le serveur tourne **et**
qu'il atteint la base de données.

Vous pouvez aussi ouvrir `http://localhost:8000/admin/` et vous connecter avec
le compte créé à l'étape 2.6.

---

## 3. Utiliser l'API

### 3.1 Se connecter et obtenir un jeton

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "VOTRE_IDENTIFIANT", "password": "VOTRE_MOT_DE_PASSE"}'
```

La réponse contient `access` (valable 8 heures) et `refresh` (valable 7 jours).

### 3.2 Appeler un endpoint protégé

```bash
curl http://localhost:8000/api/elevage/bandes-pondeuses/ \
  -H "Authorization: Bearer VOTRE_JETON_ACCESS"
```

### 3.3 Se déconnecter

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "VOTRE_JETON_REFRESH"}'
```

Le jeton `refresh` est alors invalidé et ne peut plus être utilisé.

> La connexion est limitée à **5 tentatives par minute et par adresse IP**.
> Au-delà, l'API répond `429 Too Many Requests` : attendez une minute.

### 3.4 Documentation interactive

Swagger UI : `http://localhost:8000/api/schema/swagger-ui/`
(par défaut, ses ressources sont chargées depuis un CDN : une connexion
internet est nécessaire).

Pour tester avec un outil comme Postman, utilisez `http://localhost:8000/api`
comme URL de base et l'authentification « Bearer Token ».

---

## 4. Tests et qualité du code

```bash
pytest
```

Les tests utilisent une base SQLite en mémoire : **ni Docker ni Redis ne sont
nécessaires** pour les lancer. Tous doivent passer. Pour une sortie plus
courte (sans le tableau de couverture) :

```bash
pytest -q --no-cov
```

Vérification du style, identique à celle de la CI :

```bash
ruff check .
ruff format --check .
```

Pour corriger automatiquement : `ruff check --fix .` puis `ruff format .`.

---

## 5. Rôles et permissions

Cinq rôles, d'après l'organigramme du cahier des charges :

| Rôle | Peut notamment |
|---|---|
| `proprietaire` | Tout. **Seul** à approuver ou rejeter une dépense exceptionnelle ou un investissement, et **seul** à consulter le journal d'audit. |
| `gestionnaire` | Créer les comptes utilisateurs, gérer bandes, stock, ventes et dépenses, enregistrer les encaissements, consulter le reporting. |
| `responsable_elevage` | Gérer les bandes, saisir les suivis, enregistrer les interventions vétérinaires, gérer le stock et les ventes, saisir des dépenses. |
| `ouvrier` | Saisir le suivi journalier et signaler un incident sanitaire. Lecture seule ailleurs, sans accès aux finances, au reporting ni à l'audit. |
| `comptable` | Consulter les données financières et le reporting, enregistrer un encaissement **sans avoir créé la vente** (séparation des fonctions). Ne crée ni vente ni dépense. |

Pour créer un utilisateur d'un autre rôle : `POST /api/auth/utilisateurs/`
avec `username`, `email`, `password` et `role`, en étant connecté en
propriétaire ou gestionnaire.

---

## 6. Endpoints principaux

| Préfixe | Contenu |
|---|---|
| `/api/auth/` | `token/`, `token/refresh/`, `logout/`, `utilisateurs/` |
| `/api/elevage/` | `bandes-pondeuses/`, `suivi-pondeuse/` (+ `kpi/`), `bandes-chair/` (+ `{id}/cloturer/`), `suivi-chair/` |
| `/api/biosecurite/` | `interventions/`, `incidents/` (+ `non_resolus/`) |
| `/api/stock/` | `articles/` (+ `sous_seuil/`), `mouvements/`, `inventaires/` |
| `/api/ventes/` | `clients/`, `ventes/` (+ `creances_clients/`) |
| `/api/finance/` | `depenses/` (+ `{id}/approuver/`, `{id}/rejeter/`, `compte_exploitation_mensuel/`) |
| `/api/audit/` | `journal/` (lecture seule, propriétaire uniquement) |
| `/api/reporting/` | `tableau-de-bord/`, `rapport-mensuel/`, `rapport-mensuel/export/?mois=AAAA-MM&type_export=pdf` (ou `excel`) |
| `/health/` | Sonde de santé publique |
| `/admin/` | Administration Django |

La liste complète et les champs attendus sont dans Swagger (section 3.4).

---

## 7. Architecture

Monolithe modulaire : un module métier par dossier de `apps/`, sans dépendance
directe entre eux.

```
config/
  settings/       base.py, dev.py, prod.py, test.py
  urls.py
core/
  events.py       bus d'événements interne
apps/
  accounts/       utilisateurs, rôles, authentification JWT
  elevage/        bandes pondeuses et chair, suivis journaliers
  biosecurite/    interventions vétérinaires, incidents sanitaires
  stock/          articles, mouvements, inventaires
  ventes/         clients, ventes
  finance/        dépenses, workflow d'approbation
  audit/          journal de traçabilité
  reporting/      tableau de bord, rapport mensuel, exports
requirements/     base.txt, dev.txt, prod.txt
docs/             guides de déploiement
```

Les modules communiquent par **événements** plutôt que par appels directs.
Exemples : une vente enregistrée publie `VenteEnregistree`, que le module
`stock` écoute pour décrémenter le stock ; une mortalité au-dessus du seuil
publie un événement que `biosecurite` transforme en incident sanitaire.

---

## 8. Variables d'environnement

Définies dans `.env` (modèle : `.env.example`).

| Variable | Rôle |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` en local |
| `DJANGO_SECRET_KEY` | Clé secrète : une vraie valeur aléatoire (section 2.3) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Connexion à PostgreSQL ; `DB_PORT` doit correspondre au port exposé par Docker (section 2.4) |
| `REDIS_URL` | Adresse de Redis |
| `CORS_ALLOWED_ORIGINS` | Origines autorisées à appeler l'API depuis un navigateur (adresse du futur frontend), séparées par des virgules |
| `SEUIL_ALERTE_MORTALITE_PCT` | Seuil de mortalité journalière (en %) au-delà duquel un incident est créé automatiquement. Optionnel, 5.0 par défaut |

Une variable exportée dans votre terminal l'emporte sur le fichier `.env`.

---

## 9. Problèmes fréquents

**Les requêtes restent bloquées, sans réponse.** Redis n'est pas démarré :
`docker compose up -d redis`, puis `docker compose ps`.

**`password authentication failed for user "postgres"`.** Un autre
PostgreSQL occupe le port visé. Comparez `DB_PORT` avec le port affiché par
`docker compose ps`, et regardez qui écoute sur 5432 :
`sudo ss -tlnp | grep 5432`.

**Erreur 403 sur tout, alors que vous êtes superuser.** Votre compte a un
rôle vide (cas d'un compte créé avant la correction). Corrigez-le :

```bash
python manage.py shell -c "from apps.accounts.models import Utilisateur; u = Utilisateur.objects.get(username='VOTRE_IDENTIFIANT'); u.role = 'proprietaire'; u.save()"
```

**Erreur 429 à la connexion.** Limite de 5 tentatives par minute : patientez.

**`docker compose up` échoue ou le port 8000 est occupé.** Vous avez lancé
tous les services au lieu de `db redis` (section 2.4) :
`docker compose down`, puis relancez uniquement `docker compose up -d db redis`.

**Repartir d'une base vide.** Attention, ceci **supprime toutes les données
locales** :

```bash
docker compose down -v
docker compose up -d db redis
python manage.py migrate
python manage.py createsuperuser
```

---

## 10. Contribuer

Branches :

- `main` : version stable, toujours déployable ;
- `develop` : intégration ;
- `feature/<module>-<description>`, `fix/...`, `chore/...` : une branche par
  tâche, créée depuis `develop`.

Chaque modification passe par une **Pull Request** vers `develop`. La CI
(GitHub Actions) exécute `ruff` puis `pytest` : elle doit être verte avant le
merge. Messages de commit : `feat(module): ...`, `fix(module): ...`,
`test(module): ...`, `chore(...)`.

Avant chaque commit, `pytest` et `ruff check .` doivent passer. Optionnel :
`pre-commit install` lance `ruff` automatiquement à chaque commit.

---

## 11. Déploiement

Les guides se trouvent dans `docs/` :

- `docs/DEPLOIEMENT_RENDER.md` : plateforme Render (`render.yaml`) ;
- `docs/DEPLOIEMENT.md` : serveur VPS avec Docker Compose.

Le déploiement sur Render est en cours de mise au point : ces guides n'ont pas
encore été validés de bout en bout.
