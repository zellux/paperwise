from datetime import UTC, datetime

from paperwise.application.services.documents import (
    CreateDocumentCommand,
    create_document,
    delete_document,
)
from paperwise.domain.models import Document, DocumentStatus


class FakeRepository:
    def __init__(self) -> None:
        self.saved: dict[str, Document] = {}
        self.deleted_document_ids: list[str] = []

    def save(self, document: Document) -> None:
        self.saved[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self.saved.get(document_id)

    def delete_document(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)
        self.saved.pop(document_id, None)


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, str]] = []

    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        self.enqueued.append(
            {
                "document_id": document_id,
                "blob_uri": blob_uri,
                "filename": filename,
                "content_type": content_type,
            }
        )
        return "job-123"


def test_create_document_persists_and_enqueues() -> None:
    repository = FakeRepository()
    dispatcher = FakeDispatcher()

    document, job_id = create_document(
        CreateDocumentCommand(
            filename="invoice.pdf",
            owner_id="u-1",
            blob_uri="file:///tmp/invoice.pdf",
            checksum_sha256="abc123",
            content_type="application/pdf",
            size_bytes=999,
        ),
        repository=repository,
        dispatcher=dispatcher,
    )

    assert job_id == "job-123"
    assert document.id in repository.saved
    assert dispatcher.enqueued == [
        {
            "document_id": document.id,
            "blob_uri": "file:///tmp/invoice.pdf",
            "filename": "invoice.pdf",
            "content_type": "application/pdf",
        }
    ]
    assert document.status == DocumentStatus.PROCESSING
    assert document.blob_uri == "file:///tmp/invoice.pdf"
    assert isinstance(document.created_at, datetime)
    assert document.created_at.tzinfo == UTC


def test_delete_document_delegates_to_repository() -> None:
    repository = FakeRepository()

    delete_document("doc-123", repository=repository)

    assert repository.deleted_document_ids == ["doc-123"]
