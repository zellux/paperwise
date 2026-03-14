---
title: Repository Layout
description: High-level map of the Paperwise codebase.
---

## Main directories

- `src/paperwise/server` — FastAPI entrypoint, static UI, and HTTP routes
- `src/paperwise/workers` — Celery app and background tasks
- `src/paperwise/domain` — core domain models and invariants
- `src/paperwise/application` — use cases and provider interfaces
- `src/paperwise/adapters` — provider implementations for LLM, OCR, search, and storage
- `src/paperwise/infrastructure` — config and external integrations
- `src/paperwise/events` — internal event contracts
- `tests` — unit and integration tests
- `infra` — local infrastructure definitions
- `docs` — product and design documents
- `website/docs-src` — Starlight docs source
- `website/docs` — generated static docs output
- `website` — standalone marketing site

## Storage layout

Uploaded files and processed artifacts live under the local object-store layout when running locally. Blob references are stored as relative object-store keys so the repository does not depend on machine-specific absolute paths.

## User model

Paperwise requires authenticated users. Guest access is disabled.

- `POST /users` creates a user
- `POST /users/login` returns a bearer token
- document endpoints require `Authorization: Bearer <token>`
