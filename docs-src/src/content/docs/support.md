---
title: Q&A
description: Common questions, setup notes, troubleshooting tips, and operating guidance for Paperwise.
---

## How does text extraction and OCR work in Paperwise?

Paperwise first tries to extract text directly from the document when possible. This works well for machine-readable PDFs and avoids unnecessary OCR.

When the file is a scan, image-heavy PDF, or low-quality document, Paperwise falls back to OCR based on the mode you choose in **Settings > Model Config**.

### OCR paths

- **Local Tesseract** keeps OCR on your machine using `tesseract` and `pdftoppm`.
- **LLM OCR using your main connection** sends rendered page images to the same provider family you use elsewhere.
- **Separate OCR model routing** lets you choose a dedicated OCR model independently from metadata extraction and grounded Q&A.

For OpenAI-based vision OCR, you can also tune image detail to `auto`, `low`, or `high`.

## Which models should I use?

Paperwise works well with both GPT and Gemini setups. Use task-specific models so OCR, extraction, and grounded Q&A are tuned separately.

| Task | GPT example | Gemini example | Notes |
| --- | --- | --- | --- |
| OCR | `gpt-5-mini` | `gemini-2.5-flash` | Good fast multimodal starting points for scanned PDFs and forms |
| Metadata extraction | `gpt-5-mini` | `gemini-2.5-flash` | Balanced choices for structured fields |
| Grounded Q&A | `gpt-5.1` | `gemini-2.5-pro` | Better picks for more demanding cross-document questions |
| Budget / bulk work | `gpt-5-nano` | `gemini-2.5-flash-lite` | Useful for lighter classification and triage |

If your documents are mostly clean text PDFs, start with the faster models and only move up when quality is not good enough.

## Why does OCR sometimes time out on dense PDFs?

Large page images can take longer to process. Paperwise logs per-page OCR progress and retries timed-out pages. Longer OCR request timeouts are enabled for vision calls.

## Why is CPU usage high while processing documents?

Local OCR is the most common cause. When **Local Tesseract** is enabled, Paperwise runs `tesseract` and `pdftoppm` on your machine, which can consume a lot of CPU on scans, image-heavy PDFs, and large batches.

If local CPU usage is a concern, open **Settings > Model Config** and switch **OCR Engine** away from **Local Tesseract**. If OCR auto-switch is enabled, disable it when you do not want Paperwise to fall back to local OCR after direct text extraction looks weak. You can use an LLM OCR route instead if you prefer to trade provider calls for lower local CPU load.

## How are duplicate files handled?

Documents are deduplicated by SHA256 checksum to prevent repeated ingestion of the same file content.

## Where can I get more help?

Open an issue in the repository:

- [github.com/zellux/paperwise](https://github.com/zellux/paperwise)
