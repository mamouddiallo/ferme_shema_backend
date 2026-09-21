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
