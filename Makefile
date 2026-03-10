VENV ?= .venv
PYTHON ?= python3.13
VENV_PYTHON = $(VENV)/bin/python
RUN_DIR ?= .run
LOG_DIR ?= .logs
BACKEND_PID_FILE ?= $(RUN_DIR)/backend.pid
WORKER_PID_FILE ?= $(RUN_DIR)/worker.pid
BACKEND_LOG ?= $(LOG_DIR)/backend.log
WORKER_LOG ?= $(LOG_DIR)/worker.log

.PHONY: setup deps-up deps-down backend api worker worker-bg backend-bg dev-up dev-stop dev-restart dev-status test smoke-llm

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e .[dev]

deps-up:
	docker compose -f infra/docker-compose.yml up -d

deps-down:
	docker compose -f infra/docker-compose.yml down

backend:
	$(VENV_PYTHON) -m uvicorn paperwise.server.main:app --reload

api: backend

worker:
	$(VENV_PYTHON) -m celery -A paperwise.workers.celery_app.celery_app worker --loglevel=INFO

backend-bg:
	@mkdir -p $(RUN_DIR) $(LOG_DIR)
	@if [ -f "$(BACKEND_PID_FILE)" ] && kill -0 "$$(cat "$(BACKEND_PID_FILE)")" 2>/dev/null; then \
		echo "backend already running (pid=$$(cat "$(BACKEND_PID_FILE)"))"; \
	else \
		rm -f "$(BACKEND_PID_FILE)"; \
		echo "starting backend..."; \
		nohup sh -c '$(VENV_PYTHON) -m uvicorn paperwise.server.main:app --reload' > "$(BACKEND_LOG)" 2>&1 & echo $$! > "$(BACKEND_PID_FILE)"; \
		echo "backend started (pid=$$(cat "$(BACKEND_PID_FILE)")) log=$(BACKEND_LOG)"; \
	fi

worker-bg:
	@mkdir -p $(RUN_DIR) $(LOG_DIR)
	@if [ -f "$(WORKER_PID_FILE)" ] && kill -0 "$$(cat "$(WORKER_PID_FILE)")" 2>/dev/null; then \
		echo "worker already running (pid=$$(cat "$(WORKER_PID_FILE)"))"; \
	else \
		rm -f "$(WORKER_PID_FILE)"; \
		echo "starting worker..."; \
		nohup sh -c '$(VENV_PYTHON) -m celery -A paperwise.workers.celery_app.celery_app worker --loglevel=INFO' > "$(WORKER_LOG)" 2>&1 & echo $$! > "$(WORKER_PID_FILE)"; \
		echo "worker started (pid=$$(cat "$(WORKER_PID_FILE)")) log=$(WORKER_LOG)"; \
	fi

dev-up: deps-up backend-bg worker-bg

dev-stop:
	@if [ -f "$(BACKEND_PID_FILE)" ]; then \
		pid="$$(cat "$(BACKEND_PID_FILE)")"; \
		if kill -0 "$$pid" 2>/dev/null; then \
			echo "stopping backend (pid=$$pid)..."; \
			kill "$$pid" 2>/dev/null || true; \
		fi; \
		rm -f "$(BACKEND_PID_FILE)"; \
	fi
	@if [ -f "$(WORKER_PID_FILE)" ]; then \
		pid="$$(cat "$(WORKER_PID_FILE)")"; \
		if kill -0 "$$pid" 2>/dev/null; then \
			echo "stopping worker (pid=$$pid)..."; \
			kill "$$pid" 2>/dev/null || true; \
		fi; \
		rm -f "$(WORKER_PID_FILE)"; \
	fi

dev-restart: dev-stop dev-up

dev-status:
	@echo "== Backend =="
	@if [ -f "$(BACKEND_PID_FILE)" ]; then \
		pid="$$(cat "$(BACKEND_PID_FILE)")"; \
		if kill -0 "$$pid" 2>/dev/null; then \
			echo "running (pid=$$pid) log=$(BACKEND_LOG)"; \
		else \
			echo "not running (stale pid file: $$pid)"; \
		fi; \
	else \
		echo "not running"; \
	fi
	@echo "== Worker =="
	@if [ -f "$(WORKER_PID_FILE)" ]; then \
		pid="$$(cat "$(WORKER_PID_FILE)")"; \
		if kill -0 "$$pid" 2>/dev/null; then \
			echo "running (pid=$$pid) log=$(WORKER_LOG)"; \
		else \
			echo "not running (stale pid file: $$pid)"; \
		fi; \
	else \
		echo "not running"; \
	fi
	@echo "== Dependencies (docker compose) =="
	@docker compose -f infra/docker-compose.yml ps

test:
	$(VENV_PYTHON) -m pytest

smoke-llm:
	$(VENV_PYTHON) scripts/smoke_llm.py
