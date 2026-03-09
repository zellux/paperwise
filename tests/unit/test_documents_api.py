from fastapi.testclient import TestClient

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
)
from zapis.api.main import app
from zapis.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def enqueue(self, document_id: str) -> str:
        self.enqueued.append(document_id)
        return "job-test-1"


def test_create_and_get_document() -> None:
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            json={"filename": "receipt.png", "owner_id": "user-123"},
        )
        assert create_response.status_code == 201

        payload = create_response.json()
        assert payload["status"] == "received"
        assert payload["job_id"] == "job-test-1"

        get_response = client.get(f"/documents/{payload['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payload["id"]
        assert get_response.json()["filename"] == "receipt.png"
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

