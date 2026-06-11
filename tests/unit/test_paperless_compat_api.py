from datetime import UTC, datetime

from fastapi.testclient import TestClient

from paperwise.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult
from paperwise.infrastructure.config import Settings
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.application.services.session_tokens import create_session_token
from paperwise.infrastructure.storage.local_storage import LocalStorageAdapter
from paperwise.server.routes import paperless_compat
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


def _create_user_and_token(
    client: TestClient,
    *,
    email: str = "mobile@example.com",
    full_name: str = "Mobile User",
) -> tuple[str, dict[str, str]]:
    create_response = client.post(
        "/users",
        json={
            "email": email,
            "full_name": full_name,
            "password": "strong-pass-123",
        },
    )
    assert create_response.status_code == 201
    token_response = client.post(
        "/api/token/",
        json={"username": email, "password": "strong-pass-123"},
    )
    assert token_response.status_code == 200
    return create_response.json()["id"], {"Authorization": f"Token {token_response.json()['token']}"}


def _create_user(client: TestClient, *, email: str = "mobile@example.com") -> str:
    create_response = client.post(
        "/users",
        json={
            "email": email,
            "full_name": "Mobile User",
            "password": "strong-pass-123",
        },
    )
    assert create_response.status_code == 201
    return create_response.json()["id"]


def _paperless_token(client: TestClient, *, email: str = "mobile@example.com") -> str:
    token_response = client.post(
        "/api/token/",
        json={"username": email, "password": "strong-pass-123"},
    )
    assert token_response.status_code == 200
    return token_response.json()["token"]


def test_paperless_token_is_stable_and_not_session_shaped(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path), session_ttl_seconds=60)
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings

    try:
        client = TestClient(app)
        _create_user(client)

        first_token = _paperless_token(client)
        second_token = _paperless_token(client)

        assert first_token == second_token
        assert len(first_token) == 40
        assert "." not in first_token

        profile = client.get("/api/profile/", headers={"Authorization": f"Token {first_token}"})
        assert profile.status_code == 200
        assert profile.json()["email"] == "mobile@example.com"
        assert profile.json()["auth_token"] == first_token
    finally:
        app.dependency_overrides.clear()


def test_paperless_compat_still_accepts_existing_session_tokens(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings

    try:
        client = TestClient(app)
        user_id = _create_user(client)
        session_token = create_session_token(
            user_id=user_id,
            secret=settings.auth_secret,
            ttl_seconds=settings.session_ttl_seconds,
        )

        profile = client.get("/api/profile/", headers={"Authorization": f"Token {session_token}"})
        assert profile.status_code == 200
        assert profile.json()["email"] == "mobile@example.com"
        assert profile.json()["auth_token"] == _paperless_token(client)
    finally:
        app.dependency_overrides.clear()


def test_paperless_compat_headers_apply_to_normal_and_error_responses(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings

    try:
        client = TestClient(app)
        _create_user(client)
        headers = {"Authorization": f"Token {_paperless_token(client)}"}

        for response in [
            client.get("/api/documents/", headers=headers),
            client.get("/api/config/", headers=headers),
            client.get("/api/tags/", headers=headers),
            client.get("/api/remote_version/", headers=headers),
            client.get("/api/profile/"),
        ]:
            assert response.headers["x-api-version"] == "9"
            assert response.headers["x-version"] == "2.20.15"

        unauthenticated = client.get("/api/profile/")
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["www-authenticate"] == "Token"
        assert unauthenticated.json()["detail"] == "Authentication credentials were not provided."
    finally:
        app.dependency_overrides.clear()


def _seed_document(
    repository: InMemoryDocumentRepository,
    storage: LocalStorageAdapter,
    owner_id: str,
    *,
    document_id: str = "doc-mobile",
    storage_key: str = "incoming/mobile/invoice.pdf",
    filename: str = "invoice.pdf",
    checksum: str = "abc123",
    suggested_title: str = "May Invoice",
    document_date: str = "2026-05-29",
    created_at: datetime | None = None,
    correspondent: str = "Acme Corp",
    document_type: str = "Invoice",
    tags: list[str] | None = None,
) -> None:
    blob_uri = storage.put(storage_key, b"%PDF-1.4\nmobile", "application/pdf")
    document = Document(
        id=document_id,
        filename=filename,
        owner_id=owner_id,
        blob_uri=blob_uri,
        checksum_sha256=checksum,
        content_type="application/pdf",
        size_bytes=15,
        status=DocumentStatus.READY,
        created_at=created_at or datetime(2026, 5, 29, 12, 0, tzinfo=UTC),
    )
    repository.save(document)
    tag_names = ["Finance", "Tax"] if tags is None else tags
    repository.add_correspondent(correspondent)
    repository.add_document_type(document_type)
    repository.add_tags(tag_names)
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
            suggested_title=suggested_title,
            document_date=document_date,
            correspondent=correspondent,
            document_type=document_type,
            tags=tag_names,
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=document.created_at,
        )
    )


def _seed_receipt(repository: InMemoryDocumentRepository, storage: LocalStorageAdapter, owner_id: str) -> None:
    blob_uri = storage.put("incoming/mobile/receipt.pdf", b"%PDF-1.4\nreceipt", "application/pdf")
    document = Document(
        id="doc-receipt",
        filename="receipt.pdf",
        owner_id=owner_id,
        blob_uri=blob_uri,
        checksum_sha256="def456",
        content_type="application/pdf",
        size_bytes=16,
        status=DocumentStatus.READY,
        created_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
    )
    repository.save(document)
    repository.add_correspondent("Shop Co")
    repository.add_document_type("Receipt")
    repository.add_tags(["Expense"])
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=document.id,
            suggested_title="Shop Receipt",
            document_date="2026-05-28",
            correspondent="Shop Co",
            document_type="Receipt",
            tags=["Expense"],
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

        profile = client.get("/api/profile/", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["auth_token"] == headers["Authorization"].removeprefix("Token ")

        schema = client.head("/api/schema/")
        assert schema.status_code == 200
        assert schema.headers["x-api-version"] == "9"

        ui_settings = client.get("/api/ui_settings/", headers=headers)
        assert ui_settings.status_code == 200
        assert ui_settings.json()["user"]["username"] == "mobile@example.com"
        assert "view_document" in ui_settings.json()["permissions"]
        assert "add_document" in ui_settings.json()["permissions"]
        assert ui_settings.json()["settings"]["date_display"]["date_locale"] == "en-US"
        assert ui_settings.json()["settings"]["search"]["db_only"] is False

        compat_user_id = ui_settings.json()["user"]["id"]
        compat_user = client.get(f"/api/users/{compat_user_id}/", headers=headers)
        assert compat_user.status_code == 200
        assert "view_document" in compat_user.json()["inherited_permissions"]

        groups = client.get("/api/groups/?page=1&full_perms=true&page_size=250", headers=headers)
        assert groups.status_code == 200
        assert groups.json()["results"] == []

        config = client.get("/api/config/", headers=headers)
        assert config.status_code == 200
        assert config.json()[0]["app_title"] == "Paperwise"
        assert config.json()[0]["user_args"] is None

        tasks = client.get("/api/tasks/?task_name=consume_file&acknowledged=false", headers=headers)
        assert tasks.status_code == 200
        assert tasks.json() == []

        documents = client.get("/api/documents/?page=1&page_size=10", headers=headers)
        assert documents.status_code == 200
        payload = documents.json()
        assert payload["count"] == 1
        assert payload["results"][0]["title"] == "May Invoice"
        assert isinstance(payload["results"][0]["id"], int)
        assert payload["results"][0]["tags"]
        assert payload["results"][0]["owner"] is None
        assert payload["results"][0]["permissions"]["view"] == {"users": [], "groups": []}

        document_id = payload["results"][0]["id"]
        detail = client.get(f"/api/documents/{document_id}/", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["content"] == "Invoice total for mobile client"

        download = client.get(f"/api/documents/{document_id}/download/", headers=headers)
        assert download.status_code == 200
        assert download.content == b"%PDF-1.4\nmobile"
    finally:
        app.dependency_overrides.clear()


def test_paperless_mobile_pdf_images_are_generated_once_in_derived_cache(tmp_path, monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    storage = LocalStorageAdapter(settings.object_store_root)
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[storage_dependency] = lambda: storage

    generated_paths = []

    def fake_generate_pdf_image(source_path, destination_path, *, scale_to) -> None:
        del source_path, scale_to
        generated_paths.append(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"\x89PNG\r\n\x1a\nthumb")

    monkeypatch.setattr(paperless_compat, "_generate_pdf_image", fake_generate_pdf_image)

    try:
        client = TestClient(app)
        owner_id, headers = _create_user_and_token(client)
        _seed_document(repository, storage, owner_id, document_id="doc/cache test", checksum="abc/123")

        documents = client.get("/api/documents/", headers=headers).json()
        document_id = documents["results"][0]["id"]

        first = client.get(f"/api/documents/{document_id}/thumb/", headers=headers)
        second = client.get(f"/api/documents/{document_id}/thumb/", headers=headers)
        preview_first = client.get(f"/api/documents/{document_id}/preview/", headers=headers)
        preview_second = client.get(f"/api/documents/{document_id}/preview/", headers=headers)

        assert first.status_code == 200
        assert first.headers["content-type"] == "image/png"
        assert first.content == b"\x89PNG\r\n\x1a\nthumb"
        assert second.status_code == 200
        assert second.content == first.content
        assert preview_first.status_code == 200
        assert preview_first.headers["content-type"] == "image/png"
        assert preview_second.status_code == 200
        assert preview_second.content == preview_first.content
        assert generated_paths == [
            tmp_path / "derived" / "document-thumbnails" / "doc-cache-test" / "abc-123" / "thumb.png",
            tmp_path / "derived" / "document-thumbnails" / "doc-cache-test" / "abc-123" / "preview.png",
        ]
    finally:
        app.dependency_overrides.clear()


def test_paperless_mobile_non_image_preview_returns_cached_placeholder_png(tmp_path) -> None:
    repository = InMemoryDocumentRepository()
    settings = Settings(object_store_root=str(tmp_path))
    storage = LocalStorageAdapter(settings.object_store_root)
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        owner_id, headers = _create_user_and_token(client)
        blob_uri = storage.put("incoming/mobile/wechat.md", b"# Notes\n", "text/markdown")
        document = Document(
            id="doc-markdown",
            filename="wechat.md",
            owner_id=owner_id,
            blob_uri=blob_uri,
            checksum_sha256="markdown-checksum",
            content_type="text/markdown",
            size_bytes=8,
            status=DocumentStatus.READY,
            created_at=datetime(2026, 5, 29, 12, 0, tzinfo=UTC),
        )
        repository.save(document)

        documents = client.get("/api/documents/", headers=headers).json()
        document_id = documents["results"][0]["id"]

        preview = client.get(f"/api/documents/{document_id}/preview/", headers=headers)
        thumb = client.get(f"/api/documents/{document_id}/thumb/", headers=headers)

        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert preview.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert thumb.status_code == 200
        assert thumb.headers["content-type"] == "image/png"
        assert (tmp_path / "derived" / "document-thumbnails" / "doc-markdown" / "markdown-checksum" / "preview.png").exists()
        assert (tmp_path / "derived" / "document-thumbnails" / "doc-markdown" / "markdown-checksum" / "thumb.png").exists()
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
        other_owner_id, _other_headers = _create_user_and_token(
            client,
            email="other-mobile@example.com",
            full_name="Other Mobile",
        )
        _seed_document(
            repository,
            storage,
            other_owner_id,
            document_id="doc-other",
            storage_key="incoming/mobile/other.pdf",
            filename="other.pdf",
            checksum="other123",
            suggested_title="Other Statement",
            correspondent="Other Corp",
            document_type="Statement",
            tags=["Other Tag"],
        )

        tags = client.get("/api/tags/", headers=headers).json()
        finance_tag = next(tag for tag in tags["results"] if tag["name"] == "Finance")
        assert {tag["name"] for tag in tags["results"]} == {"Finance", "Tax"}
        assert finance_tag["document_count"] == 1
        assert finance_tag["owner"] is None
        assert finance_tag["is_inbox_tag"] is False
        assert finance_tag["text_color"]

        correspondents = client.get("/api/correspondents/", headers=headers).json()
        assert {row["name"] for row in correspondents["results"]} == {"Acme Corp"}

        document_types = client.get("/api/document_types/", headers=headers).json()
        assert {row["name"] for row in document_types["results"]} == {"Invoice"}

        created_tag = client.post("/api/tags/", headers=headers, json={"name": "Mobile"})
        assert created_tag.status_code == 201
        assert created_tag.json()["name"] == "Mobile"
        assert created_tag.json()["owner"] is None

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

        selection = client.post("/api/documents/selection_data/", headers=headers, json={"document_ids": [document_id]})
        assert selection.status_code == 200
        assert selection.json() == {
            "selected_correspondents": [],
            "selected_tags": [],
            "selected_document_types": [],
            "selected_storage_paths": [],
            "selected_custom_fields": [],
        }

        bulk_download = client.post("/api/documents/bulk_download/", headers=headers, json={"documents": [document_id]})
        assert bulk_download.status_code == 200
        assert bulk_download.json() == {"content": "archive", "compression": "none", "follow_formatting": False}
    finally:
        app.dependency_overrides.clear()


def test_paperless_mobile_document_filters_use_paperless_query_params(tmp_path) -> None:
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
        _seed_document(
            repository,
            storage,
            owner_id,
            document_id="doc-mobile-2",
            storage_key="incoming/mobile/invoice-2.pdf",
            filename="invoice-2.pdf",
            checksum="abc124",
            suggested_title="June Invoice",
            document_date="2026-06-29",
            created_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
        )
        _seed_receipt(repository, storage, owner_id)

        correspondents = client.get("/api/correspondents/", headers=headers).json()["results"]
        acme_id = next(row["id"] for row in correspondents if row["name"] == "Acme Corp")
        shop_id = next(row["id"] for row in correspondents if row["name"] == "Shop Co")
        document_types = client.get("/api/document_types/", headers=headers).json()["results"]
        invoice_id = next(row["id"] for row in document_types if row["name"] == "Invoice")
        receipt_id = next(row["id"] for row in document_types if row["name"] == "Receipt")
        tags = client.get("/api/tags/", headers=headers).json()["results"]
        finance_id = next(row["id"] for row in tags if row["name"] == "Finance")

        filtered = client.get(f"/api/documents/?correspondent__id__in={acme_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        filtered = client.get(f"/api/documents/?correspondent__id__none={shop_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        filtered = client.get(f"/api/documents/?document_type__id__in={receipt_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["Shop Receipt"]

        filtered = client.get(f"/api/documents/?document_type__id__in={invoice_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        filtered = client.get(f"/api/documents/?document_type__id__none={invoice_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["Shop Receipt"]

        filtered = client.get(f"/api/documents/?tags__id__all={finance_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        filtered = client.get(f"/api/documents/?tags__id__none={finance_id}", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["Shop Receipt"]

        filtered = client.get("/api/documents/?title_content=invoice", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        filtered = client.get("/api/documents/?title_search=receipt", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["Shop Receipt"]

        filtered = client.get("/api/documents/?text=mobile%20client", headers=headers)
        assert filtered.status_code == 200
        assert [row["title"] for row in filtered.json()["results"]] == ["June Invoice", "May Invoice"]

        tagged = client.get("/api/documents/?is_tagged=1", headers=headers)
        assert tagged.status_code == 200
        assert tagged.json()["count"] == 3
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
