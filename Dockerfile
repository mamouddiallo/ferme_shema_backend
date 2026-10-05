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

# Valeurs factices UNIQUEMENT pour cette commande (syntaxe "VAR=valeur cmd"
# scope la variable à ce seul processus, sans jamais persister dans l'image
# via ENV — donc aucun risque qu'un vrai conteneur démarre avec ce secret
# par défaut si quelqu'un oublie de configurer la vraie variable au runtime).
# Sans ça, settings/prod.py lève une erreur au build (ses vérifications de
# sécurité l'exigent), et un `|| true` masquerait l'échec au lieu de le
# résoudre — exactement le piège qu'on corrige ici.
RUN DJANGO_SECRET_KEY=build-stage-uniquement DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 8000

# $PORT est fourni dynamiquement par Render ; en son absence (VPS, docker
# compose local), on retombe sur 8000 par défaut.
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]
