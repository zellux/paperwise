---
title: Dev Environment Setup
description: Commands and workflow notes for running Paperwise from source.
---

## Core commands

| Command | Purpose |
| --- | --- |
| `make setup` | Create the local virtualenv and install dependencies |
| `make setup PYTHON=python3.13` | Use Python 3.13 explicitly |
| `make deps-up` | Start local dependency services (`redis` and `postgres`) |
| `make deps-down` | Stop local dependency services |
| `make dev-up` | Start dependencies, backend, and worker in the background |
| `make dev-stop` | Stop the backend and worker started by `make dev-up` |
| `make dev-restart` | Restart the local development stack |
| `make dev-status` | Show backend, worker, and dependency status |
| `make backend` | Run the FastAPI backend from the local virtualenv |
| `make worker` | Run the Celery worker from the local virtualenv |
| `make test` | Run tests |

## Default local URLs

- App UI: `http://localhost:8000`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

## Local persistence

By default, local config uses in-memory storage. To persist data in Postgres, set:

```bash
PAPERWISE_REPOSITORY_BACKEND=postgres
PAPERWISE_POSTGRES_URL=postgresql+psycopg://paperwise:paperwise@localhost:5432/paperwise
```

Then run `make deps-up` and restart the backend.
