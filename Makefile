VENV ?= .venv
PYTHON ?= python3.13
ACTIVATE = . $(VENV)/bin/activate

.PHONY: setup deps-up deps-down backend api worker test smoke-llm

setup:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip
	$(ACTIVATE) && pip install -e .[dev]

deps-up:
	docker compose -f infra/docker-compose.yml up -d

deps-down:
	docker compose -f infra/docker-compose.yml down

backend:
	$(ACTIVATE) && uvicorn paperwise.api.main:app --reload

api: backend

worker:
	$(ACTIVATE) && celery -A paperwise.workers.celery_app.celery_app worker --loglevel=INFO

test:
	$(ACTIVATE) && pytest

smoke-llm:
	$(ACTIVATE) && python scripts/smoke_llm.py
