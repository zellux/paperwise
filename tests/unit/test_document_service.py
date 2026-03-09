from datetime import UTC, datetime

from zapis.application.services.documents import CreateDocumentCommand, create_document
from zapis.domain.models import Document, DocumentStatus


class FakeRepository:
    def __init__(self) -> None:
        self.saved: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self.saved[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self.saved.get(document_id)


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def enqueue(self, document_id: str) -> str:
        self.enqueued.append(document_id)
        return "job-123"


def test_create_document_persists_and_enqueues() -> None:
    repository = FakeRepository()
    dispatcher = FakeDispatcher()

    document, job_id = create_document(
        CreateDocumentCommand(filename="invoice.pdf", owner_id="u-1"),
        repository=repository,
        dispatcher=dispatcher,
    )

    assert job_id == "job-123"
    assert document.id in repository.saved
    assert dispatcher.enqueued == [document.id]
    assert document.status == DocumentStatus.RECEIVED
    assert isinstance(document.created_at, datetime)
    assert document.created_at.tzinfo == UTC

