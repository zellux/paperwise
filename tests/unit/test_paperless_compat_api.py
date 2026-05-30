from datetime import UTC, datetime

from fastapi.testclient import TestClient

from paperwise.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult
from paperwise.infrastructure.config import Settings
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.infrastructure.storage.local_storage import LocalStorageAdapter
from paperwise.server.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    settings_dependency,
    storage_dependency,
)
from paperwise.server.main import app


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
        del blob_uri, filename, content_type
        self.enqueued.append(document_id)
        return f"job-{document_id}"


def _create_user_and_token(client: TestClient) -> tuple[str, dict[str, str]]:
    create_response = client.post(
        "/users",
        json={
            "email": "mobile@example.com",
            "full_name": "Mobile User",
            "password": "strong-pass-123",
        },
    )
    assert create_response.status_code == 201
    token_response = client.post(
        "/api/token/",
        json={"username": "mobile@example.com", "password": "strong-pass-123"},
    )
    assert token_response.status_code == 200
    return create_response.json()["id"], {"Authorization": f"Token {token_response.json()['token']}"}


def _seed_document(repository: InMemoryDocumentRepository, storage: LocalStorageAdapter, owner_id: str) -> None:
    blob_uri = storage.put("incoming/mobile/invoice.pdf", b"%PDF-1.4\nmobile", "application/pdf")
    document = Document(
        id="doc-mobile",
        filename="invoice.pdf",
        owner_id=owner_id,
        blob_uri=blob_uri,
        checksum_sha256="abc123",
        content_type="application/pdf",
        size_bytes=15,
        status=DocumentStatus.READY,
        created_at=datetime(2026, 5, 29, 12, 0, tzinfo=UTC),
    )
    repository.save(document)
    repository.add_correspondent("Acme Corp")
    repository.add_document_type("Invoice")
    repository.add_tags(["Finance", "Tax"])
    repository.save_parse_result(
        ParseResult(
            document_id=document.id,
            parser="test",
            status="success",
            size_bytes=15,
            page_count=1,
            text_preview="Invoice total for mobile client",
            created_at=document.created_at,
        )
    )
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=document.id,
            suggested_title="May Invoice",
            document_date="2026-05-29",
            correspondent="Acme Corp",
            document_type="Invoice",
            tags=["Finance", "Tax"],
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=document.created_at,
        )
    )


def test_paperless_mobile_auth_profile_and_document_listing(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    storage = LocalStorageAdapter(settings.object_store_root)
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        owner_id, headers = _create_user_and_token(client)
        _seed_document(repository, storage, owner_id)

        profile = client.head("/api/profile/", headers=headers)
        assert profile.status_code == 200
        assert profile.headers["x-api-version"] == "9"

        schema = client.head("/api/schema/")
        assert schema.status_code == 200
        assert schema.headers["x-api-version"] == "9"

        ui_settings = client.get("/api/ui_settings/", headers=headers)
        assert ui_settings.status_code == 200
        assert ui_settings.json()["user"]["username"] == "mobile@example.com"

        documents = client.get("/api/documents/?page=1&page_size=10", headers=headers)
        assert documents.status_code == 200
        payload = documents.json()
        assert payload["count"] == 1
        assert payload["results"][0]["title"] == "May Invoice"
        assert isinstance(payload["results"][0]["id"], int)
        assert payload["results"][0]["tags"]

        document_id = payload["results"][0]["id"]
        detail = client.get(f"/api/documents/{document_id}/", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["content"] == "Invoice total for mobile client"

        download = client.get(f"/api/documents/{document_id}/download/", headers=headers)
        assert download.status_code == 200
        assert download.content == b"%PDF-1.4\nmobile"
    finally:
        app.dependency_overrides.clear()


def test_paperless_mobile_labels_stats_patch_and_stubs(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    storage = LocalStorageAdapter(settings.object_store_root)
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        owner_id, headers = _create_user_and_token(client)
        _seed_document(repository, storage, owner_id)

        tags = client.get("/api/tags/", headers=headers).json()
        finance_tag = next(tag for tag in tags["results"] if tag["name"] == "Finance")
        assert finance_tag["document_count"] == 1

        created_tag = client.post("/api/tags/", headers=headers, json={"name": "Mobile"})
        assert created_tag.status_code == 201
        assert created_tag.json()["name"] == "Mobile"

        documents = client.get("/api/documents/", headers=headers).json()
        document_id = documents["results"][0]["id"]
        patch_response = client.patch(
            f"/api/documents/{document_id}/",
            headers=headers,
            json={"title": "Updated Invoice", "tags": [finance_tag["id"]]},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Updated Invoice"
        assert patch_response.json()["tags"] == [finance_tag["id"]]

        stats = client.get("/api/statistics/", headers=headers)
        assert stats.status_code == 200
        assert stats.json()["documents_total"] == 1
        assert stats.json()["tag_count"] >= 2

        saved_views = client.get("/api/saved_views/", headers=headers)
        assert saved_views.status_code == 200
        assert saved_views.json()["results"] == []

        suggestions = client.get(f"/api/documents/{document_id}/suggestions/", headers=headers)
        assert suggestions.status_code == 200
        assert suggestions.json()["tags"] == [finance_tag["id"]]
    finally:
        app.dependency_overrides.clear()


def test_paperless_mobile_upload_endpoint_accepts_document_field(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    storage = LocalStorageAdapter(settings.object_store_root)
    dispatcher = FakeDispatcher()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher

    try:
        client = TestClient(app)
        _owner_id, headers = _create_user_and_token(client)

        upload = client.post(
            "/api/documents/post_document/",
            headers=headers,
            files={"document": ("scan.pdf", b"%PDF-1.4\nscan", "application/pdf")},
            data={"title": "Scanned Upload", "created": "2026-05-29"},
        )
        assert upload.status_code == 200
        assert upload.text.strip('"').startswith("job-")

        listed = client.get("/api/documents/", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
        assert listed.json()["results"][0]["title"] == "Scanned Upload"
        assert dispatcher.enqueued
    finally:
        app.dependency_overrides.clear()
