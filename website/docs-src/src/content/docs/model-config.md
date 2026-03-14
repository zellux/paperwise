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

## Common setup issues

- Upload blocked: configure **Metadata Extraction** first.
- Ask My Docs not available: configure **Grounded Q&A** first.
- OCR failures on scans: switch OCR to a stronger multimodal model or try `Local Tesseract` for cleaner documents.
- Custom provider not working: verify the base URL and API key in **Model Config**.

Next: [Support](/docs/support/)
