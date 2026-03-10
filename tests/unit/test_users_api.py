from fastapi.testclient import TestClient

from paperwise.server.dependencies import document_repository_dependency
from paperwise.server.main import app
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)


def test_create_list_get_user() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "owner@example.com",
                "full_name": "Owner One",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["email"] == "owner@example.com"
        assert payload["full_name"] == "Owner One"
        assert payload["is_active"] is True
        assert "password_hash" not in payload

        list_response = client.get("/users")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert len(list_payload) == 1
        assert list_payload[0]["id"] == payload["id"]

        get_response = client.get(f"/users/{payload['id']}")
        assert get_response.status_code == 200
        get_payload = get_response.json()
        assert get_payload["email"] == "owner@example.com"
    finally:
        app.dependency_overrides.clear()


def test_create_user_rejects_duplicate_email() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        payload = {
            "email": "duplicate@example.com",
            "full_name": "Owner One",
            "password": "strong-pass-123",
        }
        first = client.post("/users", json=payload)
        assert first.status_code == 201

        second = client.post("/users", json=payload)
        assert second.status_code == 400
        assert second.json()["detail"] == "User with this email already exists"
    finally:
        app.dependency_overrides.clear()


def test_login_user_success_and_failure() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "login@example.com",
                "full_name": "Login User",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201

        bad_login = client.post(
            "/users/login",
            json={"email": "login@example.com", "password": "wrong"},
        )
        assert bad_login.status_code == 401

        good_login = client.post(
            "/users/login",
            json={"email": "LOGIN@example.com", "password": "strong-pass-123"},
        )
        assert good_login.status_code == 200
        assert good_login.json()["user"]["email"] == "login@example.com"
        assert good_login.json()["access_token"]
        assert good_login.json()["token_type"] == "bearer"

        me_response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {good_login.json()['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "login@example.com"
    finally:
        app.dependency_overrides.clear()


def test_change_password_success_and_requires_current_password() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "password@example.com",
                "full_name": "Password User",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201

        login_response = client.post(
            "/users/login",
            json={"email": "password@example.com", "password": "strong-pass-123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bad_change = client.post(
            "/users/me/password",
            headers=headers,
            json={
                "current_password": "wrong-pass",
                "new_password": "new-pass-123",
            },
        )
        assert bad_change.status_code == 400
        assert bad_change.json()["detail"] == "Current password is incorrect"

        change_response = client.post(
            "/users/me/password",
            headers=headers,
            json={
                "current_password": "strong-pass-123",
                "new_password": "new-pass-123",
            },
        )
        assert change_response.status_code == 200
        assert change_response.json()["message"] == "Password updated successfully."

        old_login = client.post(
            "/users/login",
            json={"email": "password@example.com", "password": "strong-pass-123"},
        )
        assert old_login.status_code == 401

        new_login = client.post(
            "/users/login",
            json={"email": "password@example.com", "password": "new-pass-123"},
        )
        assert new_login.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_user_preferences_round_trip() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "prefs@example.com",
                "full_name": "Prefs User",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201

        login_response = client.post(
            "/users/login",
            json={"email": "prefs@example.com", "password": "strong-pass-123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        get_empty = client.get("/users/me/preferences", headers=headers)
        assert get_empty.status_code == 200
        assert get_empty.json()["preferences"] == {}

        put_response = client.put(
            "/users/me/preferences",
            headers=headers,
            json={
                "preferences": {
                    "last_view": "section-tags",
                    "ui_theme": "ledger",
                    "docs_page_size": 50,
                    "llm_provider": "openai",
                    "llm_model": "gpt-4.1-mini",
                    "llm_base_url": "https://api.openai.com/v1",
                    "llm_api_key": "sk-test",
                    "ocr_provider": "llm_separate",
                    "ocr_auto_switch": True,
                    "ocr_llm_provider": "gemini",
                    "ocr_llm_model": "gemini-2.0-flash",
                    "ocr_llm_base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "ocr_llm_api_key": "gk-test",
                    "docs_filters": {
                        "tag": ["Credit"],
                        "correspondent": [],
                        "document_type": [],
                        "status": ["ready"],
                    },
                }
            },
        )
        assert put_response.status_code == 200
        assert put_response.json()["preferences"]["last_view"] == "section-tags"
        assert put_response.json()["preferences"]["ui_theme"] == "ledger"
        assert put_response.json()["preferences"]["docs_page_size"] == 50
        assert put_response.json()["preferences"]["llm_provider"] == "openai"
        assert put_response.json()["preferences"]["llm_model"] == "gpt-4.1-mini"
        assert put_response.json()["preferences"]["ocr_provider"] == "llm_separate"
        assert put_response.json()["preferences"]["ocr_auto_switch"] is True
        assert put_response.json()["preferences"]["ocr_llm_provider"] == "gemini"
        assert put_response.json()["preferences"]["ocr_llm_model"] == "gemini-2.0-flash"

        get_saved = client.get("/users/me/preferences", headers=headers)
        assert get_saved.status_code == 200
        assert get_saved.json()["preferences"]["last_view"] == "section-tags"
        assert get_saved.json()["preferences"]["ui_theme"] == "ledger"
        assert get_saved.json()["preferences"]["docs_page_size"] == 50
        assert get_saved.json()["preferences"]["llm_provider"] == "openai"
        assert get_saved.json()["preferences"]["llm_model"] == "gpt-4.1-mini"
        assert get_saved.json()["preferences"]["ocr_provider"] == "llm_separate"
        assert get_saved.json()["preferences"]["ocr_auto_switch"] is True
        assert get_saved.json()["preferences"]["ocr_llm_provider"] == "gemini"
        assert get_saved.json()["preferences"]["ocr_llm_model"] == "gemini-2.0-flash"
        assert get_saved.json()["preferences"]["docs_filters"]["tag"] == ["Credit"]
    finally:
        app.dependency_overrides.clear()


def test_user_preferences_put_merges_without_dropping_existing_keys() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        create_response = client.post(
            "/users",
            json={
                "email": "prefs-merge@example.com",
                "full_name": "Prefs Merge",
                "password": "strong-pass-123",
            },
        )
        assert create_response.status_code == 201

        login_response = client.post(
            "/users/login",
            json={"email": "prefs-merge@example.com", "password": "strong-pass-123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        seed_response = client.put(
            "/users/me/preferences",
            headers=headers,
            json={"preferences": {"llm_total_tokens_processed": 1234}},
        )
        assert seed_response.status_code == 200
        assert seed_response.json()["preferences"]["llm_total_tokens_processed"] == 1234

        update_response = client.put(
            "/users/me/preferences",
            headers=headers,
            json={"preferences": {"last_view": "section-settings"}},
        )
        assert update_response.status_code == 200
        payload = update_response.json()["preferences"]
        assert payload["last_view"] == "section-settings"
        assert payload["llm_total_tokens_processed"] == 1234
    finally:
        app.dependency_overrides.clear()
