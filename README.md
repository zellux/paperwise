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

### Run Paperwise

```bash
git clone https://github.com/zellux/paperwise.git
cd paperwise
cp .env.docker.example .env
```

Set a strong auth secret in `.env`:

```bash
PAPERWISE_AUTH_SECRET=replace-with-a-strong-secret
```

Then start the stack:

```bash
docker compose up -d --build
```

Open Paperwise at [http://localhost:8080](http://localhost:8080).

## Run published image

Paperwise can also be deployed from the published container image instead of building from source.

The GitHub Actions publish workflow pushes images to:

```text
ghcr.io/zellux/paperwise
```

To run the latest published image:

```bash
cp .env.docker.example .env
docker compose -f docker-compose.deploy.yml up -d
```

To pin a specific release tag:

```bash
PAPERWISE_IMAGE=ghcr.io/zellux/paperwise:v0.1.0 docker compose -f docker-compose.deploy.yml up -d
```

If the GHCR package is private, make it public in the GitHub package settings before sharing it with other users.

### Run published image with `docker run`

If you are not using Compose, you must run the API, worker, Redis, and Postgres containers separately. The worker is required for background document processing after upload.

Create a Docker network first:

```bash
docker network create paperwise
```

Start Redis and Postgres:

```bash
docker run -d \
  --name paperwise-redis \
  --network paperwise \
  redis:7-alpine

docker run -d \
  --name paperwise-postgres \
  --network paperwise \
  -e POSTGRES_USER=paperwise \
  -e POSTGRES_PASSWORD=paperwise \
  -e POSTGRES_DB=paperwise \
  -v paperwise-postgres-data:/var/lib/postgresql/data \
  postgres:16-alpine
```

Start the API container:

```bash
docker run -d \
  --name paperwise-api \
  --network paperwise \
  -p 8080:8000 \
  -e PAPERWISE_ENV=docker \
  -e PAPERWISE_REDIS_URL=redis://paperwise-redis:6379/0 \
  -e PAPERWISE_REPOSITORY_BACKEND=postgres \
  -e PAPERWISE_POSTGRES_URL=postgresql+psycopg://paperwise:paperwise@paperwise-postgres:5432/paperwise \
  -e PAPERWISE_OBJECT_STORE_ROOT=/data/object-store \
  -e PAPERWISE_AUTH_SECRET=replace-with-a-strong-secret \
  -v paperwise-data:/data \
  ghcr.io/zellux/paperwise:latest
```

Start the worker container:

```bash
docker run -d \
  --name paperwise-worker \
  --network paperwise \
  -e PAPERWISE_ENV=docker \
  -e PAPERWISE_REDIS_URL=redis://paperwise-redis:6379/0 \
  -e PAPERWISE_REPOSITORY_BACKEND=postgres \
  -e PAPERWISE_POSTGRES_URL=postgresql+psycopg://paperwise:paperwise@paperwise-postgres:5432/paperwise \
  -e PAPERWISE_OBJECT_STORE_ROOT=/data/object-store \
  -e PAPERWISE_AUTH_SECRET=replace-with-a-strong-secret \
  -v paperwise-data:/data \
  ghcr.io/zellux/paperwise:latest \
  celery -A paperwise.workers.celery_app.celery_app worker --loglevel=INFO
```

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

Published-image commands:

```bash
docker compose -f docker-compose.deploy.yml ps
docker compose -f docker-compose.deploy.yml logs -f api worker
docker compose -f docker-compose.deploy.yml down
```

## License

See [LICENSE](LICENSE).
