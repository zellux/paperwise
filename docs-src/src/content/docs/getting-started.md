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
mkdir paperwise
cd paperwise
```

Create a `docker-compose.yml` file with the published image, then replace `replace-with-a-strong-secret` with your own secret:

```yaml
services:
  api:
    image: ghcr.io/zellux/paperwise:latest
    environment:
      PAPERWISE_ENV: docker
      PAPERWISE_LOG_LEVEL: INFO
      PAPERWISE_API_HOST: 0.0.0.0
      PAPERWISE_API_PORT: 8000
      PAPERWISE_REDIS_URL: redis://redis:6379/0
      PAPERWISE_REPOSITORY_BACKEND: postgres
      PAPERWISE_POSTGRES_URL: postgresql+psycopg://paperwise:paperwise@postgres:5432/paperwise
      PAPERWISE_OBJECT_STORE_ROOT: /data/object-store
      PAPERWISE_AUTH_SECRET: replace-with-a-strong-secret
      PAPERWISE_AUTH_TOKEN_TTL_SECONDS: "43200"
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    ports:
      - "8080:8000"
    volumes:
      - paperwise_data:/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 20s
    restart: unless-stopped

  worker:
    image: ghcr.io/zellux/paperwise:latest
    command: ["celery", "-A", "paperwise.workers.celery_app.celery_app", "worker", "--loglevel=INFO"]
    environment:
      PAPERWISE_ENV: docker
      PAPERWISE_LOG_LEVEL: INFO
      PAPERWISE_REDIS_URL: redis://redis:6379/0
      PAPERWISE_REPOSITORY_BACKEND: postgres
      PAPERWISE_POSTGRES_URL: postgresql+psycopg://paperwise:paperwise@postgres:5432/paperwise
      PAPERWISE_OBJECT_STORE_ROOT: /data/object-store
      PAPERWISE_AUTH_SECRET: replace-with-a-strong-secret
      PAPERWISE_AUTH_TOKEN_TTL_SECONDS: "43200"
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    volumes:
      - paperwise_data:/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: paperwise
      POSTGRES_PASSWORD: paperwise
      POSTGRES_DB: paperwise
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U paperwise -d paperwise"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  paperwise_data:
  postgres_data:
```

Start the stack:

```bash
docker compose up -d
```

Open Paperwise at `http://localhost:8080`.

### Updating

New images are published automatically when changes land on `main`.

To update a running server that uses `ghcr.io/zellux/paperwise:latest`:

```bash
docker compose pull
docker compose up -d
```

To pin a specific release, replace the image tag, for example:

```yaml
image: ghcr.io/zellux/paperwise:v0.1.0
```

Then update by changing the tag in `docker-compose.yml` and running:

```bash
docker compose pull
docker compose up -d
```

### Useful commands

| Command | What it does |
| --- | --- |
| `docker compose ps` | Show service status for the self-hosted stack. |
| `docker compose logs -f api worker` | Follow backend and worker logs. |
| `docker compose pull` | Download the latest published image tags referenced by your compose file. |
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
