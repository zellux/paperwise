from datetime import UTC, datetime, timedelta

from paperwise.application.services.document_listing import list_filtered_documents
from paperwise.domain.models import Document, DocumentStatus, User
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository


class SpyDocumentRepository(InMemoryDocumentRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls: list[dict] = []
        self.count_calls: list[dict] = []

    def list_owner_documents_with_llm_results(self, **kwargs):
        self.list_calls.append(dict(kwargs))
        return super().list_owner_documents_with_llm_results(**kwargs)

    def count_owner_documents_by_statuses(self, **kwargs):
        self.count_calls.append(dict(kwargs))
        return super().count_owner_documents_by_statuses(**kwargs)


def _document(
    document_id: str,
    *,
    owner_id: str = "user-listing",
    status: DocumentStatus = DocumentStatus.READY,
    created_at: datetime,
) -> Document:
    return Document(
        id=document_id,
        filename=f"{document_id}.pdf",
        owner_id=owner_id,
        blob_uri=f"incoming/{document_id}.pdf",
        checksum_sha256=document_id,
        content_type="application/pdf",
        size_bytes=100,
        status=status,
        created_at=created_at,
    )


def _user(created_at: datetime) -> User:
    return User(
        id="user-listing",
        email="u@example.com",
        full_name="User",
        password_hash="hash",
        is_active=True,
        created_at=created_at,
    )


def test_list_filtered_documents_uses_repository_pagination_for_simple_status_listing() -> None:
    repository = SpyDocumentRepository()
    now = datetime.now(UTC)
    repository.save(_document("ready-old", created_at=now - timedelta(minutes=3)))
    repository.save(_document("ready-mid", created_at=now - timedelta(minutes=2)))
    repository.save(_document("ready-new", created_at=now - timedelta(minutes=1)))
    repository.save(_document("processing", status=DocumentStatus.PROCESSING, created_at=now))

    listing = list_filtered_documents(
        repository=repository,
        current_user=_user(now),
        query=None,
        tag=None,
        correspondent=None,
        document_type=None,
        status=None,
        limit=1,
        offset=1,
    )

    assert [document.id for document, _metadata in listing.rows] == ["ready-mid"]
    assert listing.total == 3
    assert repository.list_calls == [
        {
            "owner_id": "user-listing",
            "limit": 1,
            "offset": 1,
            "statuses": {DocumentStatus.READY},
        }
    ]
    assert repository.count_calls == [
        {
            "owner_id": "user-listing",
            "statuses": {DocumentStatus.READY},
        }
    ]


def test_list_filtered_documents_keeps_scan_path_for_metadata_filters() -> None:
    repository = SpyDocumentRepository()
    now = datetime.now(UTC)
    repository.save(_document("ready", created_at=now))

    listing = list_filtered_documents(
        repository=repository,
        current_user=_user(now),
        query=None,
        tag=["finance"],
        correspondent=None,
        document_type=None,
        status=None,
        limit=20,
        offset=0,
    )

    assert listing.rows == []
    assert listing.total == 0
    assert repository.count_calls == []
    assert repository.list_calls[0]["limit"] == 1000
