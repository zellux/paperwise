---
title: Model Config
description: Configure provider connections and task routing for metadata extraction, grounded Q&A, and OCR.
---

Paperwise stores model connections and task routing **per user**. After signing in, open **Settings > Model Config** to configure the AI-backed parts of the product.

## Supported connection types

Paperwise currently supports:

- **OpenAI**
- **Gemini**
- **Custom (OpenAI-compatible)**

Each connection can include:

- provider
- API key
- base URL when required
- default model

## How task routing works

Paperwise lets you assign a connection and optional model override to each task:

- **Metadata Extraction**
- **Grounded Q&A**
- **OCR**

This means you can use a lighter or cheaper model for extraction and a stronger reasoning model for grounded Q&A.

## Host-local providers with Docker

If Paperwise runs in Docker and LM Studio, Ollama, llama.cpp, or another OpenAI-compatible server runs on the Docker host, use `host.docker.internal` from Paperwise.

Use a base URL like:

```text
http://host.docker.internal:1234/v1
```

Do not use `localhost` for this case. Inside Docker, `localhost` means the Paperwise container itself, not your host machine.

Both Paperwise services need access:

- `api` uses the provider for **Test Connection** and settings checks.
- `worker` uses the provider while processing documents.

On Linux Docker hosts, add this to your compose file if `host.docker.internal` is not already available:

```yaml
services:
  api:
    extra_hosts:
      - "host.docker.internal:host-gateway"

  worker:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

If the model server runs on a different machine, bind that server to a network-reachable address and use that host name or IP instead.

## Recommended first configuration

If you just want a working setup, start simple:

1. Add one provider connection.
2. Use that connection for **Metadata Extraction**.
3. Use that same connection for **Grounded Q&A**.
4. For **OCR**, choose either:
   - **LLM** if you want OCR handled through a multimodal model
   - **Local Tesseract** if you want OCR to stay local

## OCR modes

### LLM OCR

When OCR is set to **LLM**, Paperwise sends rendered page images to the selected model. This is usually better for scans, forms, image-heavy PDFs, and harder layouts.

### Local Tesseract

When OCR is set to **Local Tesseract**, OCR runs locally using `tesseract` and `pdftoppm`. This is a good default for privacy-sensitive setups and clean printed scans.

### Auto switch

Paperwise also supports an auto-switch mode so OCR is only used when direct text extraction looks weak.

## Suggested starting models

These are practical starting points, not hard requirements:

| Task | OpenAI example | Gemini example |
| --- | --- | --- |
| OCR | `gpt-5-mini` | `gemini-2.5-flash` |
| Metadata extraction | `gpt-5-mini` | `gemini-2.5-flash` |
| Grounded Q&A | `gpt-5.1` | `gemini-2.5-pro` |

If your documents are mostly clean text PDFs, start with the faster models and only move up when quality is not good enough.

### User-verified self-hosted models

Paperwise users have reported successful local processing with this Ollama split:

| Task | Ollama model |
| --- | --- |
| OCR | `minicpm-v:latest` |
| Metadata extraction | `qwen3:8b` |
| Grounded Q&A | `qwen3:8b` |

Use a vision model such as `minicpm-v:latest` for OCR because Paperwise sends rendered page images for LLM OCR. Use a text model such as `qwen3:8b` for metadata extraction and grounded Q&A because those tasks work from extracted text.

Treat these as known-working starting points for self-hosted setups, not as the only supported local models. For custom providers, configure Ollama as an OpenAI-compatible connection, for example:

```text
http://host.docker.internal:11434/v1
```

If Paperwise and Ollama run directly on the same machine outside Docker, `http://127.0.0.1:11434/v1` is usually appropriate instead.

For text PDFs, keep **Auto switch** enabled when possible. It lets Paperwise try direct text extraction before OCR, which is usually faster than sending every page image to a multimodal model.

See [Which models should I use?](/docs/support/#which-models-should-i-use) for more detailed starting recommendations and tradeoffs.

## Common setup issues

- Upload blocked: configure **Metadata Extraction** first.
- Ask My Docs not available: configure **Grounded Q&A** first.
- OCR failures on scans: switch OCR to a stronger multimodal model or try `Local Tesseract` for cleaner documents.
- Custom provider not working: verify the base URL and API key in **Model Config**. For Docker plus host-local providers, use `host.docker.internal` instead of `localhost`.

Next: [Q&A](/docs/support/)
