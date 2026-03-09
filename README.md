# zapis

AI-native document management platform (Python-first).

## Repository Layout

- `src/zapis/api` - FastAPI entrypoint and HTTP routes.
- `src/zapis/workers` - Celery app and async/background tasks.
- `src/zapis/domain` - core domain models and invariants.
- `src/zapis/application` - use cases and provider interfaces.
- `src/zapis/adapters` - provider implementations (LLM, OCR, search, storage).
- `src/zapis/infrastructure` - config and external integrations.
- `src/zapis/events` - internal event contracts.
- `tests` - unit and integration tests.
- `infra` - local infrastructure definitions (Docker Compose).
- `docs` - product/design documents.

## Quickstart (local)

```bash
cp .env.example .env.local
make setup
make deps-up
make api
```

In another shell:

```bash
make worker
```

Open [http://localhost:8000](http://localhost:8000) for the initial web UI.

## Local Development Commands

- `make setup` - create local virtualenv and install all dependencies.
- `make setup PYTHON=python3.13` - explicitly use Python 3.13 if needed.
- `make deps-up` - start local dependency services (Redis).
- `make deps-down` - stop local dependency services.
- `make api` - run FastAPI from local virtualenv.
- `make worker` - run Celery worker from local virtualenv.
- `make test` - run tests.
