COMPOSE := docker compose

.PHONY: env up down logs ps test test-api test-agent test-frontend lint format seed celery-logs

env:
	@test -f .env || (echo "Missing .env - create it as described in README (Getting started)" && exit 1)

up: env
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

test: test-api test-agent test-frontend

test-api: env
	$(COMPOSE) run --rm --no-deps api pytest

test-agent: env
	$(COMPOSE) run --rm --no-deps agent pytest

test-frontend: env
	$(COMPOSE) run --rm --no-deps frontend npm test

lint: env
	$(COMPOSE) run --rm --no-deps api ruff check .
	$(COMPOSE) run --rm --no-deps agent ruff check .
	$(COMPOSE) run --rm --no-deps frontend npm run lint

format: env
	$(COMPOSE) run --rm --no-deps api ruff format .
	$(COMPOSE) run --rm --no-deps agent ruff format .
	$(COMPOSE) run --rm --no-deps frontend npm run format

seed: env
	$(COMPOSE) exec api python -m app.seed

celery-logs: env
	$(COMPOSE) logs -f celery-worker celery-beat
