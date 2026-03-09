from pathlib import Path

from fastapi.testclient import TestClient

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    storage_dependency,
)
from zapis.api.main import app
from zapis.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from zapis.infrastructure.storage.local_storage import LocalStorageAdapter


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        self.enqueued.append(document_id)
        return "job-test-1"


def test_create_and_get_document() -> None:
    store_dir = Path("local/test-object-store")
    if store_dir.exists():
        for item in store_dir.rglob("*"):
            if item.is_file():
                item.unlink()

    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": "user-123"},
            files={"file": ("receipt.pdf", b"%PDF-sample", "application/pdf")},
        )
        assert create_response.status_code == 201

        payload = create_response.json()
        assert payload["status"] == "received"
        assert payload["job_id"] == "job-test-1"

        get_response = client.get(f"/documents/{payload['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payload["id"]
        assert get_response.json()["filename"] == "receipt.pdf"
        assert get_response.json()["content_type"] == "application/pdf"
        assert get_response.json()["size_bytes"] == 11
        assert get_response.json()["blob_uri"].startswith("file://")
        assert dispatcher.enqueued == [payload["id"]]
    finally:
        app.dependency_overrides.clear()


def test_get_document_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_parse_document_roundtrip() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": "user-parse"},
            files={"file": ("vaccine.pdf", b"%PDF-1.3\nfake-content", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{doc_id}/parse")
        assert parse_response.status_code == 200
        assert parse_response.json()["document_id"] == doc_id
        assert parse_response.json()["status"] == "parsed"
        assert parse_response.json()["page_count"] >= 1

        get_parse_response = client.get(f"/documents/{doc_id}/parse")
        assert get_parse_response.status_code == 200
        assert get_parse_response.json()["document_id"] == doc_id
    finally:
        app.dependency_overrides.clear()


def test_get_parse_result_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/parse")
        assert response.status_code == 404
        assert response.json()["detail"] == "Parse result not found"
    finally:
        app.dependency_overrides.clear()
