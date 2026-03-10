# paperwise

AI-native document management platform (Python-first).

## Repository Layout

- `src/paperwise/api` - FastAPI entrypoint and HTTP routes.
- `src/paperwise/workers` - Celery app and async/background tasks.
- `src/paperwise/domain` - core domain models and invariants.
- `src/paperwise/application` - use cases and provider interfaces.
- `src/paperwise/adapters` - provider implementations (LLM, OCR, search, storage).
- `src/paperwise/infrastructure` - config and external integrations.
- `src/paperwise/events` - internal event contracts.
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

### OpenAI metadata parsing

Set these in `.env.local` for `llm-parse`:

```bash
PAPERWISE_OPENAI_API_KEY=your_key_here
PAPERWISE_OPENAI_MODEL=gpt-4.1-mini
PAPERWISE_OPENAI_BASE_URL=https://api.openai.com/v1
```

If `PAPERWISE_OPENAI_API_KEY` is unset, `llm-parse` is disabled.

## Local Development Commands

- `make setup` - create local virtualenv and install all dependencies.
- `make setup PYTHON=python3.13` - explicitly use Python 3.13 if needed.
- `make deps-up` - start local dependency services (Redis + Postgres).
- `make deps-down` - stop local dependency services.
- `make api` - run FastAPI from local virtualenv.
- `make worker` - run Celery worker from local virtualenv.
- `make test` - run tests.
- `make smoke-llm` - upload a sample PDF to a running API and run `llm-parse`.

## Repository Backend

By default, local config uses in-memory storage:

```bash
PAPERWISE_REPOSITORY_BACKEND=memory
```

To persist data in Postgres:

```bash
PAPERWISE_REPOSITORY_BACKEND=postgres
PAPERWISE_POSTGRES_URL=postgresql+psycopg://paperwise:paperwise@localhost:5432/paperwise
```

Then run `make deps-up` and restart `make api`.

## Local Object Storage Layout

Uploaded files are stored under:

```text
local/object-store/incoming/YYYY/MM/DD/<storage_token>_<sanitized_filename>
local/object-store/incoming/YYYY/MM/DD/<storage_token>.metadata.json
local/object-store/processed/<doc_id>/<doc_id>_<sanitized_filename>
local/object-store/processed/<doc_id>/<doc_id>_<sanitized_filename>.metadata.json
```

Each metadata sidecar JSON includes the original filename, content type, checksum, and size.

To migrate existing stored files and update `documents.blob_uri` paths:

```bash
. .venv/bin/activate
python scripts/migrate_storage_layout.py --apply
```
