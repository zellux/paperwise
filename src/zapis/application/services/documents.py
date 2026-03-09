from dataclasses import dataclass
from uuid import uuid4

from zapis.application.interfaces import DocumentRepository, IngestionDispatcher
from zapis.application.use_cases import CreateDocumentInput, initialize_document
from zapis.domain.models import Document


@dataclass(slots=True)
class CreateDocumentCommand:
    filename: str
    owner_id: str


def create_document(
    command: CreateDocumentCommand,
    repository: DocumentRepository,
    dispatcher: IngestionDispatcher,
) -> tuple[Document, str]:
    """Create a document aggregate and enqueue ingestion."""
    doc_id = str(uuid4())
    document = initialize_document(
        doc_id=doc_id,
        data=CreateDocumentInput(
            filename=command.filename,
            owner_id=command.owner_id,
        ),
    )
    repository.save(document)
    job_id = dispatcher.enqueue(document.id)
    return document, job_id


def get_document(document_id: str, repository: DocumentRepository) -> Document | None:
    """Fetch a document aggregate by ID."""
    return repository.get(document_id)

