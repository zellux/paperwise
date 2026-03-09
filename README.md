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
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn zapis.api.main:app --reload
```
