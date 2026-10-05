# Déploiement sur Render — Ferme SHEMA Backend

Guide spécifique à Render, via le fichier `render.yaml` (Blueprint). Cette
voie remplace entièrement l'approche VPS décrite dans `DEPLOIEMENT.md` —
**pas besoin** de `docker-compose.prod.yml`, `Caddyfile`, ni des scripts du
dossier `infra/` : Render gère lui-même le HTTPS, les sauvegardes de la base
et l'orchestration des conteneurs.

---

## 0. Prérequis

- Le code poussé sur GitHub (`render.yaml` doit être à la racine du dépôt)
- Un compte Render (render.com) — carte bancaire requise même pour commencer
  petit, aucune offre n'est entièrement gratuite pour une stack complète

---

## 1. Créer le Blueprint

1. Dashboard Render → **New** → **Blueprint**
2. Sélectionne le dépôt `ferme_shema_backend`, branche `main`
3. Render lit `render.yaml` et affiche un aperçu des **4 ressources** qu'il
   va créer : la base PostgreSQL, Redis, le service web, le worker Celery
4. Avant de cliquer sur "Apply", renseigne les variables marquées `sync: false` :

| Variable | Valeur à mettre |
|---|---|
| `DJANGO_SECRET_KEY` | Génère-la : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | Voir piège ci-dessous ⚠️ |
| `CORS_ALLOWED_ORIGINS` | URL de ton futur frontend, ex: `https://app.fermeshema.com` |
| `SENTRY_DSN` | Laisse vide pour l'instant (optionnel) |

### ⚠️ Piège à connaître : `DJANGO_ALLOWED_HOSTS`

Render ne révèle le nom de domaine définitif (`ferme-shema-api.onrender.com`,
ou un suffixe aléatoire si ce nom est déjà pris par quelqu'un d'autre) qu'**après**
la création du service. Deux options :
- **Devine d'abord** : mets `ferme-shema-api.onrender.com` (le nom que tu as
  donné au service dans `render.yaml`) — ça fonctionne dans la majorité des cas.
- **Si le premier déploiement plante** (logs indiquant une erreur `DJANGO_ALLOWED_HOSTS`),
  va dans **Settings** du service web, copie le vrai domaine affiché en haut
  de la page, mets à jour la variable, puis clique sur **Manual Deploy → Deploy latest commit**.

---

## 2. Suivre le premier déploiement

Dans l'onglet **Logs** du service `ferme-shema-api`, tu dois voir :
```
==> Running 'python manage.py migrate --noinput'   (le preDeployCommand)
...
==> Running 'gunicorn config.wsgi:application ...'
```

Le endpoint `/health/` doit répondre `{"status": "ok"}` une fois déployé —
c'est ce que Render vérifie automatiquement pour savoir si le déploiement a
réussi (configuré via `healthCheckPath` dans `render.yaml`).

---

## 3. Créer le premier compte (superuser)

Dans le Dashboard, onglet **Shell** du service `ferme-shema-api` (terminal
directement dans le navigateur, pas besoin de SSH) :
```bash
python manage.py createsuperuser
```

---

## 4. Domaine personnalisé (optionnel)

Service `ferme-shema-api` → **Settings** → **Custom Domains** → ajoute ton
domaine, suis les instructions pour le CNAME chez ton registrar. Render gère
le certificat HTTPS automatiquement, comme pour le sous-domaine `.onrender.com`.

N'oublie pas de mettre à jour `DJANGO_ALLOWED_HOSTS` avec ce nouveau domaine
une fois actif.

---

## 5. Déploiements suivants

Chaque `git push` sur `main` déclenche un redéploiement automatique — rien
à faire de plus. Pour déployer manuellement une version précise :
Dashboard → service → **Manual Deploy** → choisir le commit.

---

## 6. Sauvegardes de la base

**Contrairement au VPS**, pas besoin du script `infra/backup_postgres.sh` —
Render effectue des sauvegardes automatiques quotidiennes sur les plans
payants de PostgreSQL. Vérifie la rétention exacte (nombre de jours
conservés) dans Dashboard → base `ferme-shema-db` → **Backups**, et ajuste
le plan si la rétention par défaut est insuffisante pour tes besoins.

---

## 7. Monitoring

- **Logs et métriques de base** (CPU, mémoire, requêtes) : onglet **Metrics**
  de chaque service, inclus nativement.
- **Alertes sur erreurs applicatives** : toujours recommandé de configurer
  `SENTRY_DSN` (voir `DEPLOIEMENT.md` section 6 pour la marche à suivre,
  identique quelle que soit la plateforme d'hébergement).

---

## Fichiers utilisés par ce chemin de déploiement

| Fichier | Utilisé par Render ? |
|---|---|
| `render.yaml` | ✅ Oui — c'est le point d'entrée |
| `Dockerfile` | ✅ Oui — Render l'utilise directement pour construire l'image |
| `docker-compose.prod.yml` | ❌ Non — spécifique au déploiement VPS |
| `Caddyfile` | ❌ Non — Render gère le HTTPS lui-même |
| `infra/*.sh` | ❌ Non — ni déploiement manuel, ni sauvegarde manuelle nécessaires |
