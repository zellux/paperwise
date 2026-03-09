from pathlib import Path

from fastapi.testclient import TestClient

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
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


class FakeLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del existing_correspondents
        del existing_document_types
        del existing_tags
        return {
            "suggested_title": "Experian Credit Report",
            "document_date": "2026-03-01",
            "correspondent": "experian.",
            "document_type": "Credit report",
            "tags": ["credit", "identity", "Identity"],
        }


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


def test_list_documents() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        for name in ("a.pdf", "b.pdf"):
            create_response = client.post(
                "/documents",
                data={"owner_id": "user-list"},
                files={"file": (name, b"%PDF-1.4\nx", "application/pdf")},
            )
            assert create_response.status_code == 201

        list_response = client.get("/documents")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) >= 2
        assert payload[0]["filename"] in {"a.pdf", "b.pdf"}
        assert "llm_metadata" in payload[0]
        assert payload[0]["llm_metadata"] is None
    finally:
        app.dependency_overrides.clear()


def test_list_documents_includes_llm_metadata_when_available() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": "user-list-llm"},
            files={"file": ("credit.pdf", b"%PDF-1.7\nexperian", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]
        llm_response = client.post(f"/documents/{doc_id}/llm-parse")
        assert llm_response.status_code == 200

        list_response = client.get("/documents")
        assert list_response.status_code == 200
        payload = list_response.json()
        target = next((item for item in payload if item["id"] == doc_id), None)
        assert target is not None
        assert target["llm_metadata"] is not None
        assert target["llm_metadata"]["document_type"].lower() == "credit report"
        assert "identity" in target["llm_metadata"]["tags"]
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


def test_llm_parse_dedupes_and_creates_taxonomy() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    repository.add_correspondent("Experian")
    repository.add_document_type("Credit Report")
    repository.add_tags(["credit"])

    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": "user-llm"},
            files={"file": ("credit.pdf", b"%PDF-1.7\nexperian", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        llm_response = client.post(f"/documents/{doc_id}/llm-parse")
        assert llm_response.status_code == 200
        payload = llm_response.json()
        assert payload["correspondent"] == "Experian"
        assert payload["document_type"] == "Credit Report"
        assert payload["tags"] == ["credit", "identity"]
        assert payload["created_correspondent"] is False
        assert payload["created_document_type"] is False
        assert payload["created_tags"] == ["identity"]

        fetch_response = client.get(f"/documents/{doc_id}/llm-parse")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["document_id"] == doc_id

        taxonomy_response = client.get("/documents/metadata/taxonomy")
        assert taxonomy_response.status_code == 200
        taxonomy = taxonomy_response.json()
        assert "Experian" in taxonomy["correspondents"]
        assert "Credit Report" in taxonomy["document_types"]
        assert "identity" in taxonomy["tags"]
    finally:
        app.dependency_overrides.clear()


def test_get_llm_parse_result_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/llm-parse")
        assert response.status_code == 404
        assert response.json()["detail"] == "LLM parse result not found"
    finally:
        app.dependency_overrides.clear()
