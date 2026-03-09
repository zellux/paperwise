from dataclasses import dataclass

from zapis.domain.models import Document, DocumentStatus


@dataclass(slots=True)
class CreateDocumentInput:
    filename: str
    owner_id: str


def initialize_document(doc_id: str, data: CreateDocumentInput) -> Document:
    """Create a new document aggregate in received state."""
    from datetime import datetime, UTC

    return Document(
        id=doc_id,
        filename=data.filename,
        owner_id=data.owner_id,
        status=DocumentStatus.RECEIVED,
        created_at=datetime.now(UTC),
    )

