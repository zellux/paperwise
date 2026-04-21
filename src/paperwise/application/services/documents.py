from dataclasses import dataclass
from uuid import uuid4

from paperwise.application.interfaces import DocumentRepository, IngestionDispatcher
from paperwise.application.use_cases import CreateDocumentInput, initialize_document
from paperwise.domain.models import Document, DocumentStatus


@dataclass(slots=True)
class CreateDocumentCommand:
    filename: str
    owner_id: str
    blob_uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int


def create_document(
    command: CreateDocumentCommand,
    repository: DocumentRepository,
    dispatcher: IngestionDispatcher,
) -> tuple[Document, str]:
    """Create a document aggregate, then move it to processing once queued."""
    doc_id = str(uuid4())
    document = initialize_document(
        doc_id=doc_id,
        data=CreateDocumentInput(
            filename=command.filename,
            owner_id=command.owner_id,
            blob_uri=command.blob_uri,
            checksum_sha256=command.checksum_sha256,
            content_type=command.content_type,
            size_bytes=command.size_bytes,
        ),
    )
    repository.save(document)
    job_id = dispatcher.enqueue(
        document_id=document.id,
        blob_uri=document.blob_uri,
        filename=document.filename,
        content_type=document.content_type,
    )
    document.status = DocumentStatus.PROCESSING
    repository.save(document)
    return document, job_id


def get_document(document_id: str, repository: DocumentRepository) -> Document | None:
    """Fetch a document aggregate by ID."""
    return repository.get(document_id)


def delete_document(document_id: str, repository: DocumentRepository) -> None:
    """Delete a document aggregate and its related records."""
    repository.delete_document(document_id)
