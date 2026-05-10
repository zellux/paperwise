from paperwise.domain.models import Document, DocumentStatus
from paperwise.infrastructure.repositories.postgres_models import DocumentRow


def coerce_document_status(value: str) -> DocumentStatus:
    legacy_map = {
        "parsing": DocumentStatus.PROCESSING,
        "parsed": DocumentStatus.PROCESSING,
        "enriching": DocumentStatus.PROCESSING,
        "failed": DocumentStatus.PROCESSING,
    }
    normalized = (value or "").strip().lower()
    if normalized in legacy_map:
        return legacy_map[normalized]
    return DocumentStatus(normalized)


def document_from_row(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        filename=row.filename,
        owner_id=row.owner_id,
        blob_uri=row.blob_uri,
        checksum_sha256=row.checksum_sha256,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        status=coerce_document_status(row.status),
        created_at=row.created_at,
    )
