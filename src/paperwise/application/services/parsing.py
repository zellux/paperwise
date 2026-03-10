from datetime import UTC, datetime

from paperwise.domain.models import ParseResult
from paperwise.infrastructure.config import get_settings
from paperwise.application.services.storage_paths import blob_ref_to_path


def parse_document_blob(
    document_id: str,
    blob_uri: str,
) -> ParseResult:
    """Stub parser for local blob content until real OCR/extract pipeline lands."""
    settings = get_settings()
    blob_path = blob_ref_to_path(blob_uri, settings.object_store_root)
    if blob_path is None:
        raise ValueError(f"Unsupported blob reference: {blob_uri}")
    raw = blob_path.read_bytes()
    is_pdf = raw.startswith(b"%PDF")
    page_count = raw.count(b"/Type /Page") if is_pdf else 0
    if is_pdf and page_count == 0:
        page_count = 1
    text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")

    return ParseResult(
        document_id=document_id,
        parser="stub-local",
        status="parsed",
        size_bytes=len(raw),
        page_count=page_count,
        text_preview=text_preview,
        created_at=datetime.now(UTC),
    )
