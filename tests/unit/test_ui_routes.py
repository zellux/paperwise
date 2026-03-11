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
