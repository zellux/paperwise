# Paperwise

Paperwise is an open-source, self-hosted document intelligence app for OCR, metadata extraction, document organization, and grounded Q&A.

Website: [paperwise.dev](https://paperwise.dev)

Docs:
- [Getting started](https://paperwise.dev/docs/getting-started/)
- [Model config](https://paperwise.dev/docs/model-config/)
- [Q&A](https://paperwise.dev/docs/support/)

## Quick start

### What you need

- Docker Engine or Docker Desktop with Compose support
- At least one model provider key for metadata extraction and grounded Q&A
- Optional: `tesseract` if you want OCR to stay local instead of using an LLM for OCR

The GitHub Actions publish workflow pushes images to:

```text
ghcr.io/zellux/paperwise
```

Create a `docker-compose.yml` file:

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

Before starting, replace `replace-with-a-strong-secret` with your own secret in both `api` and `worker`.

To pin a specific release tag, replace the image value, for example:

```yaml
image: ghcr.io/zellux/paperwise:v0.1.0
```

If the GHCR package is private, make it public in the GitHub package settings before sharing it with other users.

Open Paperwise at [http://localhost:8080](http://localhost:8080).

## First-run setup

After the app is running:

1. Create your first account.
2. Open **Settings > Model Config**.
3. Add an **OpenAI**, **Gemini**, or **Custom (OpenAI-compatible)** connection.
4. Assign models for:
   - **Metadata Extraction**
   - **Grounded Q&A**
   - **OCR**
5. Upload a few documents and test extraction or Ask My Docs.

## Suggested starting setup

- **Metadata extraction**: a fast general-purpose model
- **Grounded Q&A**: a stronger reasoning model if you need cross-document answers
- **OCR**:
  - use **LLM OCR** for scans, forms, or image-heavy PDFs
  - use **Local Tesseract** if you want OCR to stay on your machine

For more detail, use the docs:
- [Getting started](https://paperwise.dev/docs/getting-started/)
- [Model config](https://paperwise.dev/docs/model-config/)
- [Q&A](https://paperwise.dev/docs/support/)

## Common commands

```bash
docker compose ps
docker compose logs -f api worker
docker compose down
```

## License

See [LICENSE](LICENSE).
