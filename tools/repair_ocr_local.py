from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
from typing import Iterable

from paperwise.application.services.parsing import parse_document_blob
from paperwise.domain.models import Document, ParseResult
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.infrastructure.repositories.postgres_document_repository import PostgresDocumentRepository


BINARY_MARKERS = (
    "%PDF-",
    "PK\x03\x04",
)


@dataclass
class ValidationResult:
    ok: bool
    reason: str


def _is_probably_binary_ocr(text: str | None) -> bool:
    if text is None:
        return False
    sample = str(text).lstrip()
    if not sample:
        return False
    if any(sample.startswith(marker) for marker in BINARY_MARKERS):
        return True
    if "\x00" in sample[:512]:
        return True
    if "/Type /ObjStm" in sample[:512] and "stream" in sample[:512]:
        return True
    return False


def _is_pdf_document(document: Document) -> bool:
    filename = str(document.filename or "").lower()
    content_type = str(document.content_type or "").lower()
    return filename.endswith(".pdf") or "pdf" in content_type


def _validate_local_ocr_text(text: str | None) -> ValidationResult:
    if text is None:
        return ValidationResult(ok=False, reason="missing")
    if _is_probably_binary_ocr(text):
        return ValidationResult(ok=False, reason="binary_signature")

    normalized = " ".join(str(text).split())
    if not normalized:
        return ValidationResult(ok=False, reason="empty")

    letters = sum(ch.isalpha() for ch in normalized)
    words = re.findall(r"[A-Za-z]{2,}", normalized)
    if len(normalized) < 50 and letters < 20:
        return ValidationResult(ok=False, reason="too_short")
    if len(words) < 5 and letters < 40:
        return ValidationResult(ok=False, reason="too_few_words")
    return ValidationResult(ok=True, reason="ok")


def _iter_documents(repository) -> Iterable[Document]:
    offset = 0
    batch = 200
    while True:
        docs = repository.list_documents(limit=batch, offset=offset)
        if not docs:
            break
        yield from docs
        if len(docs) < batch:
            break
        offset += batch


def _build_repository(settings):
    if settings.repository_backend.lower() == "postgres":
        return PostgresDocumentRepository(settings.postgres_url)
    return InMemoryDocumentRepository()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair OCR rows that accidentally stored binary PDF bytes by reparsing with local OCR only."
    )
    parser.add_argument("--owner-id", default="", help="Optional owner_id filter.")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on number of docs to process.")
    parser.add_argument("--apply", action="store_true", help="Apply repair. Without this flag, runs dry-run only.")
    args = parser.parse_args()

    settings = get_settings()
    repository = _build_repository(settings)

    candidates: list[tuple[Document, ParseResult]] = []
    scanned = 0

    for document in _iter_documents(repository):
        scanned += 1
        if args.owner_id and document.owner_id != args.owner_id:
            continue
        parse_result = repository.get_parse_result(document.id)
        if parse_result is None:
            continue
        if not _is_probably_binary_ocr(parse_result.text_preview):
            continue
        if not _is_pdf_document(document):
            continue
        candidates.append((document, parse_result))

    if args.limit > 0:
        candidates = candidates[: args.limit]

    print(f"Scanned documents: {scanned}")
    print(f"Repair candidates (binary OCR signatures): {len(candidates)}")

    if not candidates:
        return 0

    for doc, _ in candidates[:10]:
        print(f"- candidate: {doc.id} | {doc.filename}")

    if not args.apply:
        print("Dry-run only. Re-run with --apply to perform local OCR repair.")
        return 0

    repaired = 0
    failed = 0
    skipped = 0
    validation_ok = 0
    validation_bad: dict[str, int] = {}

    for document, _ in candidates:
        try:
            result = parse_document_blob(
                document_id=document.id,
                blob_uri=document.blob_uri,
                ocr_provider="tesseract",
                llm_provider=None,
                ocr_auto_switch=False,
            )
        except Exception as exc:
            failed += 1
            print(f"! failed: {document.id} | {document.filename} | {exc}")
            continue

        if _is_probably_binary_ocr(result.text_preview):
            skipped += 1
            print(f"! still-binary-after-parse: {document.id} | {document.filename}")
            continue

        repository.save_parse_result(result)
        repaired += 1

        validation = _validate_local_ocr_text(result.text_preview)
        if validation.ok:
            validation_ok += 1
        else:
            validation_bad[validation.reason] = validation_bad.get(validation.reason, 0) + 1

    print("\nRepair summary")
    print(f"- repaired_and_saved: {repaired}")
    print(f"- failed: {failed}")
    print(f"- still_binary_after_local_parse: {skipped}")
    print(f"- local_quality_ok: {validation_ok}")
    if validation_bad:
        bad_str = ", ".join(f"{k}:{v}" for k, v in sorted(validation_bad.items()))
        print(f"- local_quality_not_ok: {bad_str}")
    else:
        print("- local_quality_not_ok: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
