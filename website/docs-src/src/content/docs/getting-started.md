---
title: Getting Started
description: Start Paperwise with Docker Compose, then finish the required first-run model setup.
---

For most self-hosted installs, start with Docker Compose.

If you want to run Paperwise from source or contribute to the codebase, see [Dev Environment Setup](/docs/reference/local-development/).

## Docker Compose

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

## Want to run from source?

If you plan to modify the code, debug the internals, or run Paperwise without Docker for the app processes, follow [Dev Environment Setup](/docs/reference/local-development/).

Next: [Model Config](/docs/model-config/)
