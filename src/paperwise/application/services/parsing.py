from datetime import UTC, datetime
from html import unescape
import re
from zipfile import BadZipFile, ZipFile

from paperwise.domain.models import ParseResult
from paperwise.infrastructure.config import get_settings
from paperwise.application.services.storage_paths import blob_ref_to_path


def _extract_text_like_segments(raw: bytes, *, max_chars: int) -> str:
    # Heuristic text extraction from binary-heavy files (for stub OCR readability).
    decoded = raw.decode("latin-1", errors="ignore").replace("\x00", " ")
    segments = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s,.;:()/#&'\"+\-]{2,}", decoded)
    cleaned: list[str] = []
    for segment in segments:
        collapsed = " ".join(segment.split())
        if len(collapsed) < 3:
            continue
        alpha = sum(ch.isalpha() for ch in collapsed)
        if alpha == 0:
            continue
        if alpha / max(len(collapsed), 1) < 0.2:
            continue
        cleaned.append(collapsed)
    if not cleaned:
        return " ".join(decoded.split())[:max_chars]
    return " ".join(cleaned)[:max_chars]


def parse_document_blob(
    document_id: str,
    blob_uri: str,
    *,
    ocr_provider: str = "llm",
) -> ParseResult:
    """Stub parser for local blob content until real OCR/extract pipeline lands."""
    settings = get_settings()
    blob_path = blob_ref_to_path(blob_uri, settings.object_store_root)
    if blob_path is None:
        raise ValueError(f"Unsupported blob reference: {blob_uri}")
    raw = blob_path.read_bytes()
    normalized_ocr = str(ocr_provider).strip().lower()
    suffix = blob_path.suffix.lower()

    is_pdf = raw.startswith(b"%PDF") or suffix == ".pdf"
    if is_pdf:
        page_count = raw.count(b"/Type /Page")
        if page_count == 0:
            page_count = 1
        # Keep a stub distinction between OCR modes so reprocess output can visibly change.
        is_llm_ocr = normalized_ocr in {"llm", "llm_separate"}
        preview_limit = 4000 if is_llm_ocr else 600
        byte_window = 24000 if is_llm_ocr else 6000
        text_preview = _extract_text_like_segments(raw[:byte_window], max_chars=preview_limit)
    elif suffix in {".txt", ".md", ".markdown"}:
        text_preview = raw[:4000].decode("utf-8", errors="replace").replace("\x00", "")
        page_count = max(1, text_preview.count("\n\n") + 1) if text_preview.strip() else 1
    elif suffix == ".docx":
        try:
            with ZipFile(blob_path) as zip_file:
                xml = zip_file.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"</w:p>", "\n", xml)
            text = re.sub(r"<[^>]+>", "", text)
            text_preview = unescape(text).replace("\x00", "").strip()
            if not text_preview:
                text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
            page_count = max(1, text.count("\n") // 30 + 1)
        except (KeyError, BadZipFile):
            text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
            page_count = 1
    else:
        text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
        page_count = 1

    parser_name = "stub-local"
    if normalized_ocr == "llm":
        parser_name = "stub-llm-ocr"
    elif normalized_ocr == "llm_separate":
        parser_name = "stub-llm-ocr-separate"

    return ParseResult(
        document_id=document_id,
        parser=parser_name,
        status="parsed",
        size_bytes=len(raw),
        page_count=page_count,
        text_preview=text_preview,
        created_at=datetime.now(UTC),
    )
