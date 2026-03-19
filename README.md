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
image: ghcr.io/zellux/paperwise:v0.1.1
```

If the GHCR package is private, make it public in the GitHub package settings before sharing it with other users.

Open Paperwise at [http://localhost:8080](http://localhost:8080).

## Before Sharing

Before you hand this off to other users, it is worth checking five things on a clean deploy:

1. Sign up and sign in both work.
2. Saving **Settings > Model Config** succeeds.
3. Uploading a document moves it out of `processing`.
4. The worker is running and document jobs complete.
5. **Ask My Docs** returns an answer for at least one test document.

## Updating

New images are published automatically when changes land on `main`.

To update a running server that uses `ghcr.io/zellux/paperwise:latest`:

```bash
docker compose pull
docker compose up -d
```

To pin a release instead of tracking `latest`, set the image tag explicitly, for example:

```yaml
image: ghcr.io/zellux/paperwise:v0.1.1
```

Then update by changing the tag in your `docker-compose.yml` and running:

```bash
docker compose pull
docker compose up -d
```

## Backups

Back up both persistent data locations:

- `postgres_data` for users, preferences, document records, and search metadata
- `paperwise_data` for uploaded files and extracted object-store data

If you only back up one of them, restore will be incomplete.

For a safe upgrade path:

1. Back up `postgres_data`.
2. Back up `paperwise_data`.
3. Run `docker compose pull`.
4. Run `docker compose up -d`.

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
docker compose logs -f postgres redis
docker compose pull
docker compose down
```

## Troubleshooting

If uploads stay stuck in `processing`:

- check that the `worker` container is running
- inspect `docker compose logs -f api worker`
- make sure Redis is healthy and reachable

If a new image was published but your server still looks old:

- run `docker compose pull`
- then run `docker compose up -d`
- if you pinned a version tag, update the tag in `docker-compose.yml`

If upload works but extraction or Ask My Docs fails:

- open **Settings > Model Config**
- confirm the required task models are assigned
- check the API logs for provider timeout or auth errors

## License

See [LICENSE](LICENSE).
