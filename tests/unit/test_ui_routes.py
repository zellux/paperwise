from datetime import UTC, datetime
import json
import re

from fastapi.testclient import TestClient

from paperwise.domain.models import ChatThread
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.dependencies import document_repository_dependency
from paperwise.server.main import app


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
        match = re.search(
            r'<script id="paperwiseInitialData" type="application/json">(.+?)</script>',
            response.text,
        )
        assert match is not None
        payload = json.loads(match.group(1))
        assert payload["authenticated"] is True
        assert payload["chat_threads"][0]["id"] == "thread-ui"
        assert payload["chat_threads"][0]["title"] == "Server rendered chat"
    finally:
        app.dependency_overrides.clear()
