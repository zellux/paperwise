VENV ?= .venv
PYTHON ?= python3.13
ACTIVATE = . $(VENV)/bin/activate

.PHONY: setup deps-up deps-down api worker test

setup:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip
	$(ACTIVATE) && pip install -e .[dev]

deps-up:
	docker compose -f infra/docker-compose.yml up -d

deps-down:
	docker compose -f infra/docker-compose.yml down

api:
	$(ACTIVATE) && uvicorn zapis.api.main:app --reload

worker:
	$(ACTIVATE) && celery -A zapis.workers.celery_app.celery_app worker --loglevel=INFO

test:
	$(ACTIVATE) && pytest
