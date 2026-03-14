---
title: Getting Started
description: Start Paperwise with Docker or a local checkout, then finish the required first-run model setup.
---

Paperwise has two main setup paths:

- **Docker Compose**: recommended for most self-hosted installs.
- **Local checkout**: best when you want to work on the codebase directly.

## Option 1: Docker Compose

Use the repository root `docker compose` stack when you want the shortest path to a working deployment.

### Prerequisites

- Docker Engine or Docker Desktop with Compose support

### Start the stack

```bash
git clone https://github.com/zellux/paperwise.git
cd paperwise
cp .env.docker.example .env
```

Set at least:

```bash
PAPERWISE_AUTH_SECRET=replace-with-a-strong-secret
```

Then build and start:

```bash
docker compose up -d --build
```

Open Paperwise at `http://localhost:8080`.

### Useful commands

| Command | What it does |
| --- | --- |
| `docker compose ps` | Show service status for the self-hosted stack. |
| `docker compose logs -f api worker` | Follow backend and worker logs. |
| `docker compose down` | Stop the stack. |

## Option 2: Local checkout and dev mode

Use this path when you want to run the backend and worker from source, debug the app, or make code changes.

### Prerequisites

- Python 3.13 recommended
- Docker available for local dependency services

### Start local development

```bash
git clone https://github.com/zellux/paperwise.git
cd paperwise
cp .env.example .env.local
make setup
make dev-up
```

If you need to choose Python explicitly:

```bash
make setup PYTHON=python3.13
```

Open Paperwise at `http://localhost:8000`.

### Useful commands

| Command | What it does |
| --- | --- |
| `make dev-status` | Show backend, worker, and dependency status. |
| `make dev-stop` | Stop the local backend and worker started by `make dev-up`. |
| `make dev-restart` | Restart the local development stack. |
| `make test` | Run the test suite. |

## Required first-run setup

After the app is running, there is one more required step: configure model connections in the web UI.

1. Create your first account or sign in. Paperwise has no guest mode.
2. Open **Settings > Model Config**.
3. Add one or more model connections.
4. Assign task models for metadata extraction, grounded Q&A, and OCR.
5. Save settings and test with a sample document.

### Minimum setup by feature

| Feature | Minimum setup |
| --- | --- |
| Document upload and extraction | A working **Metadata Extraction** connection in **Settings > Model Config** |
| Ask My Docs | A working **Grounded Q&A** connection in **Settings > Model Config** |
| OCR on scans and image PDFs | Either an **OCR** LLM connection or **Local Tesseract** enabled |

## Which path should I choose?

Use Docker if you want the shortest path to a working self-hosted install. Use local dev mode if you plan to modify the code or debug the internals.

Next: [Model Config](/model-config/)
