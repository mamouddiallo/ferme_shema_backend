from .base import *  # noqa: F401,F403

DEBUG = False

# Sert les fichiers statiques directement depuis Gunicorn, compressés et
# avec un hash dans le nom de fichier (cache navigateur efficace) — évite
# d'avoir à configurer un serveur de fichiers statiques séparé.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {  # noqa: F405
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")  # noqa: F405

if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS doit être défini en production.")

# Django exige explicitement l'origine complète (avec schéma) pour accepter
# un POST en HTTPS depuis ces hôtes — sans ça, l'admin Django refuserait la
# connexion avec une erreur CSRF malgré un domaine pourtant dans ALLOWED_HOSTS.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

if SECRET_KEY in ("insecure-dev-key-change-me", "build-stage-uniquement"):  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY doit être défini explicitement en production.")

# Render (et Caddy, côté VPS) déchiffrent le HTTPS puis transmettent en HTTP
# simple en interne. Sans cette ligne, Django croit que CHAQUE requête est
# non sécurisée et la redirige en boucle infinie à cause de
# SECURE_SSL_REDIRECT=True juste en dessous.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Durcissement sécurité, essentiel dès qu'on est exposé sur internet
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Sentry (suivi d'erreurs) : optionnel, actif seulement si SENTRY_DSN est
# renseigné — ne bloque jamais le démarrage si on choisit de ne pas l'utiliser.
SENTRY_DSN = os.environ.get("SENTRY_DSN")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% des requêtes tracées (perf), ajustable
        send_default_pii=False,  # jamais de données personnelles envoyées à Sentry
    )
