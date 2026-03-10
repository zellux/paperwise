from fastapi.testclient import TestClient

from paperwise.api.dependencies import document_repository_dependency
from paperwise.api.main import app
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
