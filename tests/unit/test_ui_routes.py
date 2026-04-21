from fastapi.testclient import TestClient

from paperwise.server.main import app


def test_ui_routes_serve_index_html() -> None:
    client = TestClient(app)
    routes = (
        "/ui/documents",
        "/ui/document",
        "/ui/collections",
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
    assert 'id="uploadProgressWrap"' in response.text
    assert 'id="uploadProgressBar"' in response.text
    assert 'id="uploadProgressStatus"' in response.text


def test_static_assets_serve_upload_progress_ui() -> None:
    client = TestClient(app)

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "showUploadProgress" in app_js.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert ".upload-progress" in styles.text
