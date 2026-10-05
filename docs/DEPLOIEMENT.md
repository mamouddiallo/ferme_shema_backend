# Déploiement en production — Ferme SHEMA Backend (VPS)

> **Deux chemins de déploiement existent dans ce projet.** Celui-ci utilise
> un VPS auto-géré (contrôle total, coût réduit, plus de configuration
> manuelle). Pour un déploiement sur une plateforme managée sans serveur à
> administrer, voir `docs/DEPLOIEMENT_RENDER.md` à la place — les deux
> partagent le même `Dockerfile`, mais tout le reste diffère.

Guide complet, de l'achat du serveur jusqu'à l'API qui répond en HTTPS.
Architecture : un seul VPS, Docker Compose, Caddy (HTTPS automatique).

---

## 0. Prérequis

- Un VPS Ubuntu 22.04 ou 24.04 (2 vCPU / 4 Go RAM suffisent largement pour
  une seule ferme). Fournisseurs courants : Hetzner, DigitalOcean, OVH, Contabo.
- Un nom de domaine (ou sous-domaine) pointant vers l'IP du VPS — ex:
  `api.fermeshema.com`.
- Un compte GitHub avec le dépôt du projet.

---

## 1. Provisionner le serveur

Connecte-toi en SSH au VPS fraîchement créé, puis installe Docker :

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

Vérifie :
```bash
docker --version
docker compose version
```

**Pare-feu minimal** (laisse passer SSH, HTTP, HTTPS, bloque le reste) :
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 2. Configurer le DNS

Chez ton registrar de domaine, crée un enregistrement **A** :
```
api.fermeshema.com  →  <IP_DU_VPS>
```
Attends la propagation (quelques minutes à quelques heures). Vérifie avec :
```bash
dig +short api.fermeshema.com
```

---

## 3. Premier déploiement (manuel)

```bash
git clone https://github.com/<ton-compte>/ferme_shema_backend.git
cd ferme_shema_backend
git checkout main

cp .env.prod.example .env
nano .env   # renseigne les vraies valeurs (voir ci-dessous)
```

**Valeurs à absolument changer dans `.env`** :
- `DJANGO_SECRET_KEY` — génère-la avec `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DJANGO_ALLOWED_HOSTS` — ton vrai domaine
- `DB_PASSWORD` — un mot de passe fort, différent de celui du dev
- `CORS_ALLOWED_ORIGINS` — l'URL réelle de ton futur frontend
- `DOMAIN` — même valeur que `DJANGO_ALLOWED_HOSTS`

Lance le premier déploiement :
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d db redis
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate
docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml up -d
```

Vérifie que tout tourne :
```bash
docker compose -f docker-compose.prod.yml ps
```

Ouvre `https://api.fermeshema.com/admin/` dans ton navigateur — Caddy a dû
obtenir un certificat Let's Encrypt automatiquement (ça peut prendre 10-30
secondes la toute première fois).

---

## 4. Mettre en place le déploiement continu (CD)

Une fois le premier déploiement manuel validé, les suivants se font tout
seuls à chaque merge sur `main`.

**Génère une clé SSH dédiée** (sur ta machine, pas sur le VPS) :
```bash
ssh-keygen -t ed25519 -C "cd-ferme-shema" -f ferme_shema_deploy_key
```

**Ajoute la clé publique sur le VPS** :
```bash
cat ferme_shema_deploy_key.pub | ssh user@vps "cat >> ~/.ssh/authorized_keys"
```

**Sur GitHub**, va dans *Settings → Secrets and variables → Actions* du
dépôt, et ajoute ces 4 secrets :

| Nom | Valeur |
|---|---|
| `VPS_HOST` | L'IP ou le domaine du VPS |
| `VPS_USER` | Ton utilisateur SSH sur le VPS |
| `VPS_SSH_KEY` | Le contenu de `ferme_shema_deploy_key` (la clé **privée**) |
| `VPS_PROJECT_PATH` | Le chemin absolu du projet sur le VPS, ex: `/home/user/ferme_shema_backend` |

Crée aussi un environnement GitHub nommé `production` (*Settings →
Environments*) — ça permet d'exiger une validation manuelle avant chaque
déploiement si tu veux ce garde-fou en plus.

À partir de maintenant, chaque `git push` sur `main` déclenche
automatiquement `infra/deploy.sh` sur le serveur.

---

## 5. Sauvegardes automatiques

```bash
crontab -e
```

Ajoute cette ligne (sauvegarde tous les jours à 3h du matin) :
```
0 3 * * * /home/user/ferme_shema_backend/infra/backup_postgres.sh >> /var/log/ferme_shema_backup.log 2>&1
```

**Teste la restauration au moins une fois**, sur un environnement qui n'est
pas la production (ou juste après une sauvegarde fraîche, avant d'avoir de
vraies données importantes) :
```bash
./infra/restore_postgres.sh /var/backups/ferme_shema/ferme_shema_XXXXXXXX.sql.gz
```
Une sauvegarde qu'on n'a jamais essayé de restaurer n'est qu'une promesse,
pas une garantie.

---

## 6. Monitoring des erreurs (Sentry, optionnel mais recommandé)

1. Crée un compte sur [sentry.io](https://sentry.io) (gratuit pour un petit volume)
2. Crée un projet Django, récupère le DSN fourni
3. Ajoute-le dans `.env` sur le VPS : `SENTRY_DSN=https://...`
4. Redéploie (`bash infra/deploy.sh`)

À partir de là, toute erreur serveur en production t'envoie une alerte
automatique avec la trace complète.

---

## 7. Opérations courantes

**Voir les logs en direct** :
```bash
docker compose -f docker-compose.prod.yml logs -f web
```

**Redéployer manuellement** (si besoin, en dehors de la CD) :
```bash
bash infra/deploy.sh
```

**Revenir en arrière en cas de problème** :
```bash
git log --oneline -5          # repérer le commit stable précédent
git reset --hard <commit_ok>
bash infra/deploy.sh
```

**Consulter l'état des conteneurs** :
```bash
docker compose -f docker-compose.prod.yml ps
```
