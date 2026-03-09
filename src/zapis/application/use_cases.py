from dataclasses import dataclass

from zapis.domain.models import Document, DocumentStatus


@dataclass(slots=True)
class CreateDocumentInput:
    filename: str
    owner_id: str
    blob_uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int


def initialize_document(doc_id: str, data: CreateDocumentInput) -> Document:
    """Create a new document aggregate in received state."""
    from datetime import datetime, UTC

    return Document(
        id=doc_id,
        filename=data.filename,
        owner_id=data.owner_id,
        blob_uri=data.blob_uri,
        checksum_sha256=data.checksum_sha256,
        content_type=data.content_type,
        size_bytes=data.size_bytes,
        status=DocumentStatus.RECEIVED,
        created_at=datetime.now(UTC),
    )
