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
make dev-up
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

## User System (MVP)

The API now includes basic user management and login:

- `POST /users` - create a user (`email`, `full_name`, `password`)
- `GET /users` - list users
- `GET /users/{user_id}` - fetch a user profile
- `POST /users/login` - verify credentials
- `GET /users/me` - validate bearer token and return current user

Passwords are stored as PBKDF2-SHA256 hashes.

Document endpoints require `Authorization: Bearer <token>` from `POST /users/login`.
Guest access is disabled.

## Local Development Commands

- `make setup` - create local virtualenv and install all dependencies.
- `make setup PYTHON=python3.13` - explicitly use Python 3.13 if needed.
- `make deps-up` - start local dependency services (Redis + Postgres).
- `make deps-down` - stop local dependency services.
- `make dev-up` - start deps + backend + worker in background (recommended).
- `make dev-stop` - stop background backend/worker started by `make dev-up`.
- `make dev-restart` - restart deps + backend + worker after code changes.
- `make dev-status` - show backend/worker pid status and docker dependency status.
- `make backend` - run FastAPI backend from local virtualenv.
- `make api` - alias for `make backend` (kept for backward compatibility).
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

Then run `make deps-up` and restart `make backend`.

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
