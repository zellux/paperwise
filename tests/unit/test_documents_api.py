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
        assert payload["status"] == "processing"
        assert payload["job_id"] == "job-test-1"

        get_response = client.get(f"/documents/{payload['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payload["id"]
        assert get_response.json()["filename"] == "receipt.pdf"
        assert get_response.json()["content_type"] == "application/pdf"
        assert get_response.json()["size_bytes"] == 11
        assert get_response.json()["blob_uri"].startswith("file://")
        assert dispatcher.enqueued == [payload["id"]]

        file_response = client.get(f"/documents/{payload['id']}/file")
        assert file_response.status_code == 200
        assert file_response.content == b"%PDF-sample"
        assert file_response.headers["content-type"].startswith("application/pdf")
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


def test_get_document_file_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/file")
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
        get_response = client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "ready"
        assert "/processed/" in get_response.json()["blob_uri"]

        file_response = client.get(f"/documents/{doc_id}/file")
        assert file_response.status_code == 200
        assert file_response.headers["content-type"].startswith("application/pdf")
        assert file_response.content == b"%PDF-1.7\nexperian"

        list_response = client.get("/documents")
        assert list_response.status_code == 200
        payload = list_response.json()
        target = next((item for item in payload if item["id"] == doc_id), None)
        assert target is not None
        assert target["llm_metadata"] is not None
        assert target["llm_metadata"]["document_type"].lower() == "credit report"
        assert "Identity" in target["llm_metadata"]["tags"]
    finally:
        app.dependency_overrides.clear()


def test_list_documents_supports_metadata_filters() -> None:
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
        ready_response = client.post(
            "/documents",
            data={"owner_id": "user-filter"},
            files={"file": ("credit.pdf", b"%PDF-1.7\nexperian", "application/pdf")},
        )
        assert ready_response.status_code == 201
        ready_id = ready_response.json()["id"]
        llm_response = client.post(f"/documents/{ready_id}/llm-parse")
        assert llm_response.status_code == 200

        pending_response = client.post(
            "/documents",
            data={"owner_id": "user-filter"},
            files={"file": ("pending.pdf", b"%PDF-1.4\npending", "application/pdf")},
        )
        assert pending_response.status_code == 201
        pending_id = pending_response.json()["id"]

        by_tag = client.get("/documents?tag=identity")
        assert by_tag.status_code == 200
        by_tag_ids = {item["id"] for item in by_tag.json()}
        assert ready_id in by_tag_ids
        assert pending_id not in by_tag_ids

        by_correspondent = client.get("/documents?correspondent=experian")
        assert by_correspondent.status_code == 200
        by_correspondent_ids = {item["id"] for item in by_correspondent.json()}
        assert ready_id in by_correspondent_ids
        assert pending_id not in by_correspondent_ids

        by_type = client.get("/documents?document_type=credit%20report")
        assert by_type.status_code == 200
        by_type_ids = {item["id"] for item in by_type.json()}
        assert ready_id in by_type_ids
        assert pending_id not in by_type_ids

        by_status = client.get("/documents?status=processing")
        assert by_status.status_code == 200
        by_status_ids = {item["id"] for item in by_status.json()}
        assert pending_id in by_status_ids
        assert ready_id not in by_status_ids

        by_multi = client.get("/documents?status=processing&status=ready")
        assert by_multi.status_code == 200
        by_multi_ids = {item["id"] for item in by_multi.json()}
        assert pending_id in by_multi_ids
        assert ready_id in by_multi_ids
    finally:
        app.dependency_overrides.clear()


def test_list_pending_documents_excludes_ready() -> None:
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
        pending_create_response = client.post(
            "/documents",
            data={"owner_id": "user-pending"},
            files={"file": ("pending.pdf", b"%PDF-1.4\npending", "application/pdf")},
        )
        assert pending_create_response.status_code == 201
        pending_id = pending_create_response.json()["id"]

        ready_create_response = client.post(
            "/documents",
            data={"owner_id": "user-pending"},
            files={"file": ("ready.pdf", b"%PDF-1.4\nready", "application/pdf")},
        )
        assert ready_create_response.status_code == 201
        ready_id = ready_create_response.json()["id"]
        llm_response = client.post(f"/documents/{ready_id}/llm-parse")
        assert llm_response.status_code == 200

        pending_response = client.get("/documents/pending")
        assert pending_response.status_code == 200
        pending_docs = pending_response.json()
        pending_ids = {item["id"] for item in pending_docs}
        assert pending_id in pending_ids
        assert ready_id not in pending_ids
    finally:
        app.dependency_overrides.clear()


def test_restart_pending_documents_requeues_non_ready_only() -> None:
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
        pending_create_response = client.post(
            "/documents",
            data={"owner_id": "user-restart"},
            files={"file": ("pending.pdf", b"%PDF-1.4\npending", "application/pdf")},
        )
        assert pending_create_response.status_code == 201
        pending_id = pending_create_response.json()["id"]

        ready_create_response = client.post(
            "/documents",
            data={"owner_id": "user-restart"},
            files={"file": ("ready.pdf", b"%PDF-1.4\nready", "application/pdf")},
        )
        assert ready_create_response.status_code == 201
        ready_id = ready_create_response.json()["id"]
        llm_response = client.post(f"/documents/{ready_id}/llm-parse")
        assert llm_response.status_code == 200

        restart_response = client.post("/documents/pending/restart?limit=200")
        assert restart_response.status_code == 200
        payload = restart_response.json()
        assert payload["restarted_count"] == 1
        assert payload["skipped_ready_count"] >= 1

        assert dispatcher.enqueued.count(pending_id) == 2
        assert dispatcher.enqueued.count(ready_id) == 1
    finally:
        app.dependency_overrides.clear()


def test_update_document_metadata_upserts_and_updates_taxonomy() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    repository.add_correspondent("Experian")
    repository.add_document_type("Credit Report")
    repository.add_tags(["Credit"])

    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": "user-edit"},
            files={"file": ("statement.pdf", b"%PDF-1.7\nstatement", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        update_response = client.patch(
            f"/documents/{doc_id}/metadata",
            json={
                "suggested_title": "March Statement",
                "document_date": "2026-03-05",
                "correspondent": "experian",
                "document_type": "credit report",
                "tags": ["credit", "financial"],
            },
        )
        assert update_response.status_code == 200
        payload = update_response.json()
        assert payload["suggested_title"] == "March Statement"
        assert payload["correspondent"] == "Experian"
        assert payload["document_type"] == "Credit Report"
        assert payload["tags"] == ["Credit", "Financial"]
        assert payload["created_tags"] == ["Financial"]

        detail_response = client.get(f"/documents/{doc_id}/detail")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["llm_metadata"]["suggested_title"] == "March Statement"
        assert detail["document"]["status"] == "ready"

        history_response = client.get(f"/documents/{doc_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()
        event_types = {event["event_type"] for event in history}
        assert "metadata_changed" in event_types
        assert "tags_added" in event_types

        patch_events = [event for event in history if event["source"] == "api.patch_metadata"]
        assert patch_events
        assert all(event["actor_type"] == "user" for event in patch_events)
        assert all(event["actor_id"] == "user-edit" for event in patch_events)
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

        get_response = client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "processing"

        get_parse_response = client.get(f"/documents/{doc_id}/parse")
        assert get_parse_response.status_code == 200
        assert get_parse_response.json()["document_id"] == doc_id
    finally:
        app.dependency_overrides.clear()


def test_reprocess_document_requeues_and_sets_processing() -> None:
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
            data={"owner_id": "user-reprocess"},
            files={"file": ("credit.pdf", b"%PDF-1.7\nexperian", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        llm_response = client.post(f"/documents/{doc_id}/llm-parse")
        assert llm_response.status_code == 200
        assert client.get(f"/documents/{doc_id}").json()["status"] == "ready"

        reprocess_response = client.post(f"/documents/{doc_id}/reprocess")
        assert reprocess_response.status_code == 200
        payload = reprocess_response.json()
        assert payload["id"] == doc_id
        assert payload["status"] == "processing"
        assert payload["job_id"] == "job-test-1"
        assert dispatcher.enqueued.count(doc_id) == 2

        history_response = client.get(f"/documents/{doc_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()
        reprocess_events = [event for event in history if event["source"] == "api.reprocess"]
        assert reprocess_events
        assert reprocess_events[0]["event_type"] == "processing_restarted"
        assert reprocess_events[0]["changes"]["status"]["after"] == "processing"

        get_response = client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "processing"
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
        assert payload["tags"] == ["Credit", "Identity"]
        assert payload["created_correspondent"] is False
        assert payload["created_document_type"] is False
        assert payload["created_tags"] == ["Identity"]

        get_response = client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "ready"
        assert "/processed/" in get_response.json()["blob_uri"]

        fetch_response = client.get(f"/documents/{doc_id}/llm-parse")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["document_id"] == doc_id

        taxonomy_response = client.get("/documents/metadata/taxonomy")
        assert taxonomy_response.status_code == 200
        taxonomy = taxonomy_response.json()
        assert "Experian" in taxonomy["correspondents"]
        assert "Credit Report" in taxonomy["document_types"]
        assert "Identity" in taxonomy["tags"]

        tag_stats_response = client.get("/documents/metadata/tag-stats")
        assert tag_stats_response.status_code == 200
        tag_stats = tag_stats_response.json()
        assert {"tag": "Credit", "document_count": 1} in tag_stats
        assert {"tag": "Identity", "document_count": 1} in tag_stats

        history_response = client.get(f"/documents/{doc_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()
        event_types = {event["event_type"] for event in history}
        assert "metadata_changed" in event_types
        assert "tags_added" in event_types
        assert "processing_completed" in event_types
        assert "file_moved" in event_types

        llm_events = [event for event in history if event["source"] == "api.llm_parse"]
        assert llm_events
        assert all(event["actor_type"] == "user" for event in llm_events)
        assert all(event["actor_id"] == "user-llm" for event in llm_events)
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


def test_get_document_history_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/history")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_metadata_update_preserves_acronyms_in_correspondent_and_tags() -> None:
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
            data={"owner_id": "user-case"},
            files={"file": ("letters.pdf", b"%PDF-1.7\nletters", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        update_response = client.patch(
            f"/documents/{doc_id}/metadata",
            json={
                "suggested_title": "Case Check",
                "document_date": "2026-03-08",
                "correspondent": "PPMG Pediatrics",
                "document_type": "general document",
                "tags": ["PPMG", "abc store"],
            },
        )
        assert update_response.status_code == 200
        payload = update_response.json()
        assert payload["correspondent"] == "PPMG Pediatrics"
        assert payload["tags"] == ["PPMG", "Abc Store"]
    finally:
        app.dependency_overrides.clear()
