from datetime import UTC, datetime
import json
import re

from fastapi.testclient import TestClient

from paperwise.domain.models import (
    ChatThread,
    Document,
    DocumentHistoryEvent,
    DocumentStatus,
    HistoryActorType,
    HistoryEventType,
    LLMParseResult,
    ParseResult,
    UserPreference,
)
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


def test_ui_routes_render_active_nav_server_side() -> None:
    client = TestClient(app)
    expected_active_hrefs = {
        "/ui/documents": "/ui/documents",
        "/ui/document": "/ui/documents",
        "/ui/tags": "/ui/tags",
        "/ui/document-types": "/ui/document-types",
        "/ui/pending": "/ui/pending",
        "/ui/upload": "/ui/upload",
        "/ui/activity": "/ui/activity",
        "/ui/search": "/ui/search",
        "/ui/grounded-qa": "/ui/grounded-qa",
        "/ui/settings": "/ui/settings",
        "/ui/settings/account": "/ui/settings",
    }

    for route, active_href in expected_active_hrefs.items():
        response = client.get(route)
        assert response.status_code == 200
        active_links = re.findall(r'<a\b[^>]*class="[^"]*\bactive\b[^"]*"[^>]*href="([^"]+)"', response.text)
        assert active_links == [active_href]


def test_ui_routes_load_page_specific_scripts() -> None:
    client = TestClient(app)

    assert "/static/documents.js" in client.get("/ui/documents").text
    assert "/static/document.js" in client.get("/ui/document").text
    assert "/static/search.js" in client.get("/ui/search").text
    assert "/static/search.js" in client.get("/ui/grounded-qa").text
    assert "/static/catalog.js" in client.get("/ui/tags").text
    assert "/static/catalog.js" in client.get("/ui/document-types").text
    assert "/static/pending.js" in client.get("/ui/pending").text
    assert "/static/upload.js" in client.get("/ui/upload").text
    assert "/static/settings.js" in client.get("/ui/settings").text
    assert "/static/pending.js" not in client.get("/ui/documents").text


def test_static_assets_do_not_keep_legacy_tag_renderers() -> None:
    client = TestClient(app)

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "createTagFilterButton" not in app_js.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert ".tag-pill-button" not in styles.text


def test_static_assets_keep_auth_state_cookie_only() -> None:
    client = TestClient(app)

    html = client.get("/ui/documents")
    assert html.status_code == 200

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert 'document.documentElement.classList.toggle("has-session", signedIn)' in app_js.text
    assert 'apiFetch("/users/me")' not in app_js.text


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
    assert 'id="search-section-keyword"' in response.text
    assert 'id="search-section-ask"' not in response.text
    assert "Search and Ask Your Docs" not in response.text
    assert 'id="section-upload"' not in response.text


def test_grounded_qa_ui_does_not_include_keyword_search_shell() -> None:
    client = TestClient(app)
    response = client.get("/ui/grounded-qa")

    assert response.status_code == 200
    assert 'id="section-search"' in response.text
    assert 'id="search-section-ask"' in response.text
    assert 'id="search-section-keyword"' not in response.text
    assert "Keyword Search" not in response.text


def test_static_assets_serve_upload_progress_ui() -> None:
    client = TestClient(app)

    upload_js = client.get("/static/upload.js")
    assert upload_js.status_code == 200
    assert "showUploadProgress" in upload_js.text

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
        assert payload["current_user"]["email"] == "chat-ui@example.com"
        assert payload["chat_threads"][0]["id"] == "thread-ui"
        assert payload["chat_threads"][0]["title"] == "Server rendered chat"
        assert '<button type="button" class="thread-button" data-thread-id="thread-ui">' in response.text
        assert '<span class="thread-title">Server rendered chat</span>' in response.text

        threads_partial = client.get("/ui/partials/chat-threads?active_thread_id=thread-ui&q=server")
        assert threads_partial.status_code == 200
        threads_partial_payload = threads_partial.json()
        assert threads_partial_payload["chat_threads"][0]["id"] == "thread-ui"
        assert '<li class="thread-item active">' in threads_partial_payload["thread_list_html"]
        assert "Server rendered chat" in threads_partial_payload["thread_list_html"]

        search_payload = _initial_data_from_response(client.get("/ui/search").text)
        assert "chat_threads" not in search_payload
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
        repository.save_parse_result(
            ParseResult(
                document_id="doc-tax",
                parser="test-parser",
                status="success",
                size_bytes=123,
                page_count=1,
                text_preview="OCR preview for the tax notice.",
                created_at=datetime(2026, 5, 2, 1, 2, 3, tzinfo=UTC),
            )
        )
        repository.append_history_events(
            [
                DocumentHistoryEvent(
                    id="history-tax",
                    document_id="doc-tax",
                    event_type=HistoryEventType.METADATA_CHANGED,
                    actor_type=HistoryActorType.USER,
                    actor_id=user_id,
                    source="test.ui",
                    changes={"suggested_title": {"before": "", "after": "Tax Notice"}},
                    created_at=datetime(2026, 5, 2, 1, 3, 4, tzinfo=UTC),
                )
            ]
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
        assert documents_payload["user_preferences"]["llm_total_tokens_processed"] == 42
        assert "Total documents: 2" in documents_html
        assert "Processing: 0" in documents_html
        assert 'data-doc-id="doc-tax"' in documents_html
        assert "Tax Notice" in documents_html
        assert '<span class="status-badge status-ready">READY</span>' in documents_html
        assert '<a class="btn" href="/ui/document?id=doc-tax" title="Open document">Open</a>' in documents_html
        assert (
            '<a class="btn btn-muted" href="/documents/doc-tax/file" target="_blank" '
            'rel="noopener noreferrer" title="View file">View</a>'
        ) in documents_html
        assert 'data-delete-doc-id="doc-tax"' in documents_html
        assert "icon-action-button" not in documents_html

        detail_html = client.get("/ui/document?id=doc-tax").text
        detail_payload = _initial_data_from_response(detail_html)
        assert detail_payload["document_detail"]["document"]["id"] == "doc-tax"
        assert detail_payload["document_detail"]["ocr_text_preview"] == "OCR preview for the tax notice."
        assert detail_payload["document_history"][0]["id"] == "history-tax"
        assert '<code id="detailDocId" class="document-detail-value">doc-tax</code>' in detail_html
        assert re.search(r'<input\b[^>]*id="metaTitle"[^>]*value="Tax Notice"', detail_html)
        assert "OCR preview for the tax notice." in detail_html
        assert "Metadata changed" in detail_html
        assert "suggested_title: (empty) -&gt; Tax Notice" in detail_html

        filtered_documents_html = client.get("/ui/documents?tag=Tax").text
        filtered_documents_payload = _initial_data_from_response(filtered_documents_html)
        assert filtered_documents_payload["documents_total"] == 1
        assert [item["id"] for item in filtered_documents_payload["documents"]] == ["doc-tax"]
        assert "Tax Notice" in filtered_documents_html
        assert "Utility Bill" not in filtered_documents_html

        paged_documents_html = client.get("/ui/documents?page_size=1&page=2").text
        paged_documents_payload = _initial_data_from_response(paged_documents_html)
        assert paged_documents_payload["documents_page"] == 2
        assert paged_documents_payload["documents_page_size"] == 1
        assert paged_documents_payload["documents_total"] == 2
        assert "Page 2 / 2" in paged_documents_html

        tags_payload = _initial_data_from_response(client.get("/ui/tags").text)
        assert tags_payload["tag_stats"] == [
            {"tag": "Finance", "document_count": 2},
            {"tag": "Tax", "document_count": 1},
        ]
        tags_html = client.get("/ui/tags").text
        assert '<td data-label="Tag">Finance</td>' in tags_html
        assert '<td data-label="Documents">2</td>' in tags_html
        assert (
            '<a class="btn" href="/ui/documents?tag=Finance" '
            'title="View documents for tag Finance">View Docs</a>'
        ) in tags_html
        assert "icon-action-button" not in tags_html

        types_html = client.get("/ui/document-types").text
        types_payload = _initial_data_from_response(types_html)
        assert types_payload["document_type_stats"] == [
            {"document_type": "Invoice", "document_count": 1},
            {"document_type": "Notice", "document_count": 1},
        ]
        assert '<td data-label="Document Type">Invoice</td>' in types_html
        assert (
            '<a class="btn" href="/ui/documents?document_type=Invoice" '
            'title="View documents for type Invoice">View Docs</a>'
        ) in types_html
        assert "icon-action-button" not in types_html

        activity_html = client.get("/ui/activity").text
        activity_payload = _initial_data_from_response(activity_html)
        assert activity_payload["activity_total_tokens"] == 42
        assert [item["llm_metadata"]["suggested_title"] for item in activity_payload["activity_documents"]] == [
            "Tax Notice",
            "Utility Bill",
        ]
        assert "LLM tokens processed: 42" in activity_html
        assert "Tax Notice" in activity_html
        assert '<span class="status-badge status-ready">READY</span>' in activity_html
        assert '<a class="btn" href="/ui/document?id=doc-tax" title="Open document">Open</a>' in activity_html
        assert (
            '<a class="btn btn-muted" href="/documents/doc-tax/file" target="_blank" '
            'rel="noopener noreferrer" title="View file">View</a>'
        ) in activity_html
        assert "icon-action-button" not in activity_html

        _save_pending_document(repository, doc_id="doc-pending", owner_id=user_id, title="Pending File")
        documents_with_pending_html = client.get("/ui/documents").text
        assert "Processing: 1" in documents_with_pending_html
        pending_html = client.get("/ui/pending").text
        pending_payload = _initial_data_from_response(pending_html)
        assert pending_payload["pending_documents"][0]["id"] == "doc-pending"
        assert pending_payload["current_user"]["email"] == "catalog-ui@example.com"
        assert 'data-pending-doc-id="doc-pending"' in pending_html
        assert "Pending File" in pending_html
        assert '<span class="status-badge status-processing">PROCESSING</span>' in pending_html

        documents_partial = client.get("/ui/partials/documents?page_size=1&page=1")
        assert documents_partial.status_code == 200
        documents_partial_payload = documents_partial.json()
        assert documents_partial_payload["documents_total"] == 2
        assert documents_partial_payload["documents_processing_count"] == 1
        assert 'data-doc-id="doc-tax"' in documents_partial_payload["table_body_html"]
        assert '<a class="btn" href="/ui/document?id=doc-tax" title="Open document">Open</a>' in documents_partial_payload["table_body_html"]

        tags_partial = client.get("/ui/partials/tags?sort_by=tag&sort_dir=desc")
        assert tags_partial.status_code == 200
        tags_partial_payload = tags_partial.json()
        assert [item["tag"] for item in tags_partial_payload["tag_stats"]] == ["Tax", "Finance"]
        assert '<a class="btn" href="/ui/documents?tag=Tax" ' in tags_partial_payload["table_body_html"]

        types_partial = client.get("/ui/partials/document-types?sort_by=document_type&sort_dir=asc")
        assert types_partial.status_code == 200
        types_partial_payload = types_partial.json()
        assert [item["document_type"] for item in types_partial_payload["document_type_stats"]] == [
            "Invoice",
            "Notice",
        ]
        assert '<td data-label="Document Type">Invoice</td>' in types_partial_payload["table_body_html"]

        activity_partial = client.get("/ui/partials/activity?limit=1")
        assert activity_partial.status_code == 200
        activity_partial_payload = activity_partial.json()
        assert activity_partial_payload["activity_total_tokens"] == 42
        assert len(activity_partial_payload["activity_documents"]) == 1
        assert '<a class="btn" href="/ui/document?id=doc-tax" title="Open document">Open</a>' in activity_partial_payload["table_body_html"]

        pending_partial = client.get("/ui/partials/pending")
        assert pending_partial.status_code == 200
        pending_partial_payload = pending_partial.json()
        assert pending_partial_payload["pending_documents"][0]["id"] == "doc-pending"
        assert 'data-pending-doc-id="doc-pending"' in pending_partial_payload["table_body_html"]

        document_partial = client.get("/ui/partials/document?id=doc-tax")
        assert document_partial.status_code == 200
        document_partial_payload = document_partial.json()
        assert document_partial_payload["document_id"] == "doc-tax"
        assert document_partial_payload["text"]["detailSizeBytes"] == "100 B (100 bytes)"
        assert document_partial_payload["inputs"]["metaTitle"] == "Tax Notice"
        assert "suggested_title: (empty) -&gt; Tax Notice" in document_partial_payload["history_html"]

        settings_payload = _initial_data_from_response(client.get("/ui/settings/models").text)
        assert settings_payload["current_user"]["email"] == "catalog-ui@example.com"
        assert settings_payload["user_preferences"]["llm_total_tokens_processed"] == 42
    finally:
        app.dependency_overrides.clear()
