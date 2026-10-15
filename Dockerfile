FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système minimales pour psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

# Valeurs factices uniquement pour le build (écrasées au runtime par Render)
ENV DJANGO_SECRET_KEY=build-stage-uniquement \
    DJANGO_ALLOWED_HOSTS=localhost

RUN python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 8000

CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]