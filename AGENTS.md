# AGENTS.md

## Project Context

- Paperwise is a self-hosted document intelligence app for OCR, metadata extraction, document organization, and grounded Q&A.
- Backend stack: FastAPI app in `src/`, Celery worker for async processing, Redis/Postgres in local/dev deploys.
- Frontend is server-rendered/static assets in `src/paperwise/server/static/`; there is no separate frontend build step for normal app UI edits.

## Key Paths

- API entry point: `src/paperwise/server/main.py`
- Main document routes: `src/paperwise/server/routes/documents.py`
- Parsing/OCR pipeline: `src/paperwise/application/services/parsing.py`
- History event assembly: `src/paperwise/application/services/history.py`
- Worker pipeline: `src/paperwise/workers/tasks.py`
- Tests: `tests/unit/`

## Local Workflow

- Create the env with `make setup`.
- Run the app locally with `make dev-up`; check status with `make dev-status`; stop with `make dev-stop`.
- Run tests with `uv run pytest` or `make test`.
- For static UI edits, a quick syntax check with `node --check src/paperwise/server/static/js/app.js` is useful.

## Repo-Specific Notes

- OCR can run via local Tesseract or remote LLM routing; `ocr_auto_switch` can still invoke local Tesseract even when OCR is otherwise set to LLM.
- Document history is important product behavior here. If you change processing, parsing, OCR, or metadata flows, check whether history events should also change.

## Commit Messages

- Check recent `git log` history before committing and follow the prevailing commit message format.
- For this repository, prefer Conventional Commit style messages such as `feat(ui): ...`, `fix(api): ...`, or `chore(release): ...`.
