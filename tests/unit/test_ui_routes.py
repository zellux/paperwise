from datetime import UTC, datetime
import json
import re

from fastapi.testclient import TestClient

from paperwise.domain.models import ChatThread, Document, DocumentStatus, LLMParseResult, UserPreference
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.dependencies import document_repository_dependency
from paperwise.server.main import app


def _initial_data_from_response(html: str) -> dict:
    match = re.search(
        r'<script id="paperwiseInitialData" type="application/json">(.+?)</script>',
        html,
    )
    assert match is not None
    return json.loads(match.group(1))


def _save_ready_document(
    repository: InMemoryDocumentRepository,
    *,
    doc_id: str,
    owner_id: str,
    title: str,
    document_type: str,
    tags: list[str],
) -> None:
    created_at = datetime(2026, 5, 2, tzinfo=UTC)
    repository.save(
        Document(
            id=doc_id,
            filename=f"{doc_id}.pdf",
            owner_id=owner_id,
            blob_uri=f"local://{doc_id}.pdf",
            checksum_sha256=f"{doc_id:0<64}"[:64],
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.READY,
            created_at=created_at,
        )
    )
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=doc_id,
            suggested_title=title,
            document_date="2026-05-02",
            correspondent="Paperwise",
            document_type=document_type,
            tags=tags,
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=created_at,
        )
    )


def _save_pending_document(
    repository: InMemoryDocumentRepository,
    *,
    doc_id: str,
    owner_id: str,
    title: str,
) -> None:
    created_at = datetime(2026, 5, 3, tzinfo=UTC)
    repository.save(
        Document(
            id=doc_id,
            filename=f"{doc_id}.pdf",
            owner_id=owner_id,
            blob_uri=f"local://{doc_id}.pdf",
            checksum_sha256=f"{doc_id:0<64}"[:64],
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.PROCESSING,
            created_at=created_at,
        )
    )
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=doc_id,
            suggested_title=title,
            document_date=None,
            correspondent="",
            document_type="",
            tags=[],
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=created_at,
        )
    )


def test_ui_routes_serve_index_html() -> None:
    client = TestClient(app)
    routes = (
        "/ui/documents",
        "/ui/document",
        "/ui/search",
        "/ui/grounded-qa",
        "/ui/tags",
        "/ui/document-types",
        "/ui/pending",
        "/ui/upload",
        "/ui/activity",
        "/ui/settings",
        "/ui/settings/account",
        "/ui/settings/display",
        "/ui/settings/models",
    )
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "<!doctype html>" in response.text.lower()


def test_static_assets_serve_clickable_tag_ui() -> None:
    client = TestClient(app)

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "createTagFilterButton" in app_js.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert ".tag-pill-button" in styles.text


def test_upload_ui_includes_batch_progress_shell() -> None:
    client = TestClient(app)
    response = client.get("/ui/upload")

    assert response.status_code == 200
    assert 'id="section-upload"' in response.text
    assert 'id="section-search"' not in response.text
    assert 'id="section-docs"' not in response.text
    assert 'id="uploadProgressWrap"' in response.text
    assert 'id="uploadProgressBar"' in response.text
    assert 'id="uploadProgressStatus"' in response.text


def test_search_ui_does_not_include_upload_shell() -> None:
    client = TestClient(app)
    response = client.get("/ui/search")

    assert response.status_code == 200
    assert 'id="section-search"' in response.text
    assert 'id="section-upload"' not in response.text


def test_static_assets_serve_upload_progress_ui() -> None:
    client = TestClient(app)

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "showUploadProgress" in app_js.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert ".upload-progress" in styles.text


def test_grounded_qa_ui_includes_initial_chat_threads_for_cookie_session() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "chat-ui@example.com",
                "full_name": "Chat UI",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]
        repository.save_chat_thread(
            ChatThread(
                id="thread-ui",
                owner_id=user_id,
                title="Server rendered chat",
                messages=[{"role": "user", "content": "hello"}],
                token_usage={"total_tokens": 3, "llm_requests": 1},
                created_at=datetime(2026, 5, 2, tzinfo=UTC),
                updated_at=datetime(2026, 5, 2, 1, tzinfo=UTC),
            )
        )

        login_response = client.post(
            "/users/login",
            json={"email": "chat-ui@example.com", "password": "strong-pass-123"},
        )
        assert login_response.status_code == 200

        response = client.get("/ui/grounded-qa")
        assert response.status_code == 200
        assert '<html lang="en" class="has-session">' in response.text
        payload = _initial_data_from_response(response.text)
        assert payload["authenticated"] is True
        assert payload["chat_threads"][0]["id"] == "thread-ui"
        assert payload["chat_threads"][0]["title"] == "Server rendered chat"
    finally:
        app.dependency_overrides.clear()


def test_catalog_ui_pages_include_initial_data_for_cookie_session() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "catalog-ui@example.com",
                "full_name": "Catalog UI",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]
        _save_ready_document(
            repository,
            doc_id="doc-tax",
            owner_id=user_id,
            title="Tax Notice",
            document_type="Notice",
            tags=["Tax", "Finance"],
        )
        _save_ready_document(
            repository,
            doc_id="doc-bill",
            owner_id=user_id,
            title="Utility Bill",
            document_type="Invoice",
            tags=["Finance"],
        )
        repository.save_user_preference(
            UserPreference(user_id=user_id, preferences={"llm_total_tokens_processed": 42})
        )

        login_response = client.post(
            "/users/login",
            json={"email": "catalog-ui@example.com", "password": "strong-pass-123"},
        )
        assert login_response.status_code == 200

        documents_html = client.get("/ui/documents").text
        documents_payload = _initial_data_from_response(documents_html)
        assert documents_payload["documents_total"] == 2
        assert documents_payload["documents_processing_count"] == 0
        assert "Total documents: 2" in documents_html
        assert "Processing: 0" in documents_html
        assert 'data-doc-id="doc-tax"' in documents_html
        assert "Tax Notice" in documents_html

        tags_payload = _initial_data_from_response(client.get("/ui/tags").text)
        assert tags_payload["tag_stats"] == [
            {"tag": "Finance", "document_count": 2},
            {"tag": "Tax", "document_count": 1},
        ]
        tags_html = client.get("/ui/tags").text
        assert '<td data-label="Tag">Finance</td>' in tags_html
        assert '<td data-label="Documents">2</td>' in tags_html

        types_html = client.get("/ui/document-types").text
        types_payload = _initial_data_from_response(types_html)
        assert types_payload["document_type_stats"] == [
            {"document_type": "Invoice", "document_count": 1},
            {"document_type": "Notice", "document_count": 1},
        ]
        assert '<td data-label="Document Type">Invoice</td>' in types_html

        activity_html = client.get("/ui/activity").text
        activity_payload = _initial_data_from_response(activity_html)
        assert activity_payload["activity_total_tokens"] == 42
        assert [item["llm_metadata"]["suggested_title"] for item in activity_payload["activity_documents"]] == [
            "Tax Notice",
            "Utility Bill",
        ]
        assert "LLM tokens processed: 42" in activity_html
        assert "Tax Notice" in activity_html

        _save_pending_document(repository, doc_id="doc-pending", owner_id=user_id, title="Pending File")
        documents_with_pending_html = client.get("/ui/documents").text
        assert "Processing: 1" in documents_with_pending_html
        pending_html = client.get("/ui/pending").text
        pending_payload = _initial_data_from_response(pending_html)
        assert pending_payload["pending_documents"][0]["id"] == "doc-pending"
        assert 'data-pending-doc-id="doc-pending"' in pending_html
        assert "Pending File" in pending_html
    finally:
        app.dependency_overrides.clear()
