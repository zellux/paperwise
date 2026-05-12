from pathlib import Path
from datetime import UTC, datetime
import io
from zipfile import ZipFile

import httpx
from fastapi.testclient import TestClient

from paperwise.application.services import llm_connection_test
from paperwise.server.routes import documents as documents_routes
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
    storage_dependency,
)
from paperwise.server.main import app
from paperwise.domain.models import (
    Collection,
    DocumentChunk,
    DocumentHistoryEvent,
    DocumentStatus,
    HistoryActorType,
    HistoryEventType,
    LLMParseResult,
    ParseResult,
    User,
)
from paperwise.domain.models import UserPreference
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.infrastructure.storage.local_storage import LocalStorageAdapter


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
    def __init__(self) -> None:
        self.calls = 0
        self.ocr_calls = 0
        self.image_ocr_calls = 0
        self.tool_calls = 0
        self._model = "metadata-test-model"

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        self.calls += 1
        return {
            "suggested_title": "Experian Credit Report",
            "document_date": "2026-03-01",
            "correspondent": "experian.",
            "document_type": "Credit report",
            "tags": ["credit", "identity", "Identity"],
        }

    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        self.ocr_calls += 1
        return text_preview

    def extract_ocr_text_from_images(
        self,
        *,
        filename: str,
        image_data_urls: list[str],
    ) -> str:
        del filename
        del image_data_urls
        self.image_ocr_calls += 1
        return "OCR TEST 123"

    def answer_with_tools(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
    ) -> dict:
        del messages
        del tools
        self.tool_calls += 1
        return {"role": "assistant", "content": "Paperwise model config test passed.", "tool_calls": []}


class FakeFailingLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        request = httpx.Request("POST", "https://api.example.test/v1/chat/completions")
        response = httpx.Response(
            401,
            request=request,
            json={"error": {"message": "Invalid API key: sk-bad", "type": "invalid_request_error"}},
        )
        response.raise_for_status()


TEST_USER = User(
    id="user-123",
    email="user-123@example.com",
    full_name="User Test",
    password_hash="pbkdf2_sha256$1$aa$bb",
    is_active=True,
    created_at=datetime.now(UTC),
)


def _build_docx_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        zip_file.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ),
        )
        zip_file.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
    return buffer.getvalue()


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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
        assert get_response.json()["blob_uri"].startswith("incoming/")
        assert dispatcher.enqueued == [payload["id"]]

        file_response = client.get(f"/documents/{payload['id']}/file")
        assert file_response.status_code == 200
        assert file_response.content == b"%PDF-sample"
        assert file_response.headers["content-type"].startswith("application/pdf")
    finally:
        app.dependency_overrides.clear()


def test_create_document_truncates_long_storage_filename(tmp_path: Path) -> None:
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(tmp_path / "object-store"))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    long_filename = f"{'hospital-bill-complaint-program-' * 12}.pdf"

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": (long_filename, b"%PDF-long-name", "application/pdf")},
        )
        assert create_response.status_code == 201
        document = repository.get(create_response.json()["id"])
        assert document is not None
        assert document.filename == long_filename

        blob_path = tmp_path / "object-store" / document.blob_uri
        assert blob_path.exists()
        assert len(blob_path.name.encode("utf-8")) <= 255
        assert blob_path.name.endswith(".pdf")
    finally:
        app.dependency_overrides.clear()


def test_create_and_get_image_document() -> None:
    store_dir = Path("local/test-object-store")
    if store_dir.exists():
        for item in store_dir.rglob("*"):
            if item.is_file():
                item.unlink()

    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\nfake-image", "image/png")},
        )
        assert create_response.status_code == 201

        payload = create_response.json()
        get_response = client.get(f"/documents/{payload['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["filename"] == "receipt.png"
        assert get_response.json()["content_type"] == "image/png"

        file_response = client.get(f"/documents/{payload['id']}/file")
        assert file_response.status_code == 200
        assert file_response.headers["content-type"].startswith("image/png")
        assert file_response.content == b"\x89PNG\r\n\x1a\nfake-image"
    finally:
        app.dependency_overrides.clear()


def test_create_document_rejects_unsupported_upload_type() -> None:
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter("local/test-object-store")
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        response = client.post(
            "/documents",
            files={"file": ("malware.exe", b"MZfake", "application/x-msdownload")},
        )
        assert response.status_code == 415
        assert "Unsupported upload type" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_document_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_delete_document_removes_file_metadata_and_related_records() -> None:
    store_dir = Path("local/test-object-store")
    if store_dir.exists():
        for item in store_dir.rglob("*"):
            if item.is_file():
                item.unlink()

    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("statement.pdf", b"%PDF-delete-me", "application/pdf")},
        )
        assert create_response.status_code == 201
        document_id = create_response.json()["id"]

        document = repository.get(document_id)
        assert document is not None
        blob_path = store_dir / document.blob_uri
        metadata_path = blob_path.with_name(f"{blob_path.name.split('_', 1)[0]}.metadata.json")
        assert blob_path.exists()
        assert metadata_path.exists()

        repository.save_parse_result(
            ParseResult(
                document_id=document_id,
                parser="test",
                status="ok",
                size_bytes=12,
                page_count=1,
                text_preview="Delete me",
                created_at=datetime.now(UTC),
            )
        )
        repository.save_llm_parse_result(
            LLMParseResult(
                document_id=document_id,
                suggested_title="Delete Me",
                document_date="2026-04-20",
                correspondent="Paperwise",
                document_type="Statement",
                tags=["Delete"],
                created_correspondent=False,
                created_document_type=False,
                created_tags=[],
                created_at=datetime.now(UTC),
            )
        )
        repository.append_history_events(
            [
                DocumentHistoryEvent(
                    id="evt-delete-1",
                    document_id=document_id,
                    event_type=HistoryEventType.METADATA_CHANGED,
                    actor_type=HistoryActorType.USER,
                    actor_id=TEST_USER.id,
                    source="test",
                    changes={"field": "value"},
                    created_at=datetime.now(UTC),
                )
            ]
        )
        repository.replace_document_chunks(
            document_id=document_id,
            owner_id=TEST_USER.id,
            chunks=[
                DocumentChunk(
                    id="chunk-delete-1",
                    document_id=document_id,
                    owner_id=TEST_USER.id,
                    chunk_index=0,
                    content="Delete me",
                    token_count=2,
                    created_at=datetime.now(UTC),
                )
            ],
        )
        collection = Collection(
            id="collection-delete-1",
            owner_id=TEST_USER.id,
            name="Cleanup Test",
            description="",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        repository.create_collection(collection)
        repository.add_collection_documents(
            collection.id,
            [document_id],
            added_at=datetime.now(UTC),
        )

        delete_response = client.delete(f"/documents/{document_id}")
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        get_response = client.get(f"/documents/{document_id}")
        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Document not found"
        assert not blob_path.exists()
        assert not metadata_path.exists()
        assert repository.get(document_id) is None
        assert repository.get_parse_result(document_id) is None
        assert repository.get_llm_parse_result(document_id) is None
        assert repository.list_history(document_id) == []
        assert repository.list_document_chunks(document_id) == []
        assert repository.list_collection_document_ids(collection.id) == []
    finally:
        app.dependency_overrides.clear()


def test_delete_document_not_found() -> None:
    repository = InMemoryDocumentRepository()
    storage = LocalStorageAdapter("local/test-object-store")
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        response = client.delete("/documents/missing-doc")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_list_documents_supports_offset_pagination() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        for name in ("first.pdf", "second.pdf", "third.pdf"):
            response = client.post(
                "/documents",
                files={"file": (name, f"%PDF-1.7\n{name}".encode("utf-8"), "application/pdf")},
            )
            assert response.status_code == 201

        full_response = client.get("/documents?limit=3&status=processing")
        assert full_response.status_code == 200
        full_payload = full_response.json()
        assert len(full_payload) == 3

        paged_response = client.get("/documents?limit=1&offset=1&status=processing")
        assert paged_response.status_code == 200
        paged_payload = paged_response.json()
        assert len(paged_payload) == 1
        assert paged_payload[0]["id"] == full_payload[1]["id"]
    finally:
        app.dependency_overrides.clear()


def test_list_documents_paginates_after_filtering() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        created_ids: list[str] = []
        for name in ("first.pdf", "second.pdf", "third.pdf", "fourth.pdf"):
            response = client.post(
                "/documents",
                files={"file": (name, f"%PDF-1.7\n{name}".encode("utf-8"), "application/pdf")},
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        newest_document = repository.get(created_ids[-1])
        assert newest_document is not None
        newest_document.owner_id = "different-user-id"
        repository.save(newest_document)

        count_response = client.get("/documents/count?status=processing")
        assert count_response.status_code == 200
        assert count_response.json()["total"] == 3

        paged_response = client.get("/documents?limit=2&offset=0&status=processing")
        assert paged_response.status_code == 200
        paged_payload = paged_response.json()
        assert len(paged_payload) == 2
        assert [item["id"] for item in paged_payload] == [created_ids[2], created_ids[1]]
    finally:
        app.dependency_overrides.clear()


def test_list_documents_supports_sorting() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        for name in ("gamma.pdf", "alpha.pdf", "beta.pdf"):
            response = client.post(
                "/documents",
                files={"file": (name, f"%PDF-1.7\n{name}".encode("utf-8"), "application/pdf")},
            )
            assert response.status_code == 201

        default_response = client.get("/documents?limit=3&status=processing")
        assert default_response.status_code == 200
        assert [item["filename"] for item in default_response.json()] == [
            "beta.pdf",
            "alpha.pdf",
            "gamma.pdf",
        ]

        ascending_response = client.get("/documents?limit=3&status=processing&sort_by=title&sort_dir=asc")
        assert ascending_response.status_code == 200
        assert [item["filename"] for item in ascending_response.json()] == [
            "alpha.pdf",
            "beta.pdf",
            "gamma.pdf",
        ]

        descending_response = client.get("/documents?limit=3&status=processing&sort_by=title&sort_dir=desc")
        assert descending_response.status_code == 200
        assert [item["filename"] for item in descending_response.json()] == [
            "gamma.pdf",
            "beta.pdf",
            "alpha.pdf",
        ]
    finally:
        app.dependency_overrides.clear()


def test_count_documents_with_filters() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        first_response = client.post(
            "/documents",
            files={"file": ("count-1.pdf", b"%PDF-1.7\na", "application/pdf")},
        )
        assert first_response.status_code == 201
        first_doc_id = first_response.json()["id"]
        first_llm = client.post(f"/documents/{first_doc_id}/llm-parse")
        assert first_llm.status_code == 200

        second_response = client.post(
            "/documents",
            files={"file": ("count-2.pdf", b"%PDF-1.7\nb", "application/pdf")},
        )
        assert second_response.status_code == 201
        second_doc_id = second_response.json()["id"]
        second_doc = repository.get(second_doc_id)
        assert second_doc is not None
        second_doc.owner_id = "different-user-id"
        repository.save(second_doc)
        repository.save_llm_parse_result(
            LLMParseResult(
                document_id=second_doc_id,
                suggested_title="Other User Doc",
                document_date="2026-03-01",
                correspondent="Other Corp",
                document_type="Statement",
                tags=["PrivateTag"],
                created_correspondent=True,
                created_document_type=True,
                created_tags=["PrivateTag"],
                created_at=datetime.now(UTC),
            )
        )

        count_response = client.get("/documents/count?status=ready")
        assert count_response.status_code == 200
        assert count_response.json()["total"] == 1

        tag_count_response = client.get("/documents/count?status=ready&tag=Credit")
        assert tag_count_response.status_code == 200
        assert tag_count_response.json()["total"] == 1

        search_count_response = client.get("/documents/count?status=ready&q=Experian")
        assert search_count_response.status_code == 200
        assert search_count_response.json()["total"] == 1

        search_list_response = client.get("/documents?status=ready&q=Credit%20Report")
        assert search_list_response.status_code == 200
        assert len(search_list_response.json()) == 1
    finally:
        app.dependency_overrides.clear()


def test_upload_dedupes_by_owner_and_checksum() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        content = b"%PDF-1.7\nsame-content"
        first_response = client.post(
            "/documents",
            files={"file": ("dup.pdf", content, "application/pdf")},
        )
        assert first_response.status_code == 201
        first_payload = first_response.json()
        assert first_payload["job_id"] == "job-test-1"

        second_response = client.post(
            "/documents",
            files={"file": ("dup-copy.pdf", content, "application/pdf")},
        )
        assert second_response.status_code == 201
        second_payload = second_response.json()
        assert second_payload["id"] == first_payload["id"]
        assert second_payload["job_id"] is None
        assert dispatcher.enqueued == [first_payload["id"]]
    finally:
        app.dependency_overrides.clear()


def test_upload_and_parse_text_document() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("notes.txt", b"PPMG Pediatrics follow-up notes", "text/plain")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{doc_id}/parse")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["parser"] == "stub-llm-ocr"
        assert "PPMG Pediatrics" in payload["text_preview"]
    finally:
        app.dependency_overrides.clear()


def test_upload_and_parse_docx_document() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={
                "file": (
                    "visit.docx",
                    _build_docx_bytes("PPMG Pediatrics annual visit"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{doc_id}/parse")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["parser"] == "stub-llm-ocr"
        assert "PPMG Pediatrics annual visit" in payload["text_preview"]
    finally:
        app.dependency_overrides.clear()


def test_parse_uses_llm_ocr_mode_from_user_preferences() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        repository.save_user_preference(
            UserPreference(
                user_id=TEST_USER.id,
                preferences={"ocr_provider": "llm"},
            )
        )
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("llm-ocr.pdf", b"%PDF-1.7\nsample", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{doc_id}/parse")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["parser"] == "stub-llm-ocr"
    finally:
        app.dependency_overrides.clear()


def test_parse_uses_separate_llm_ocr_mode_from_user_preferences() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        repository.save_user_preference(
            UserPreference(
                user_id=TEST_USER.id,
                preferences={"ocr_provider": "llm_separate"},
            )
        )
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("llm-separate-ocr.pdf", b"%PDF-1.7\nsample", "application/pdf")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{doc_id}/parse")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["parser"] == "stub-llm-ocr-separate"
    finally:
        app.dependency_overrides.clear()


def test_document_endpoints_require_authentication() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository

    try:
        client = TestClient(app)
        response = client.get("/documents")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
    finally:
        app.dependency_overrides.clear()


def test_get_document_file_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        for name in ("a.pdf", "b.pdf"):
            create_response = client.post(
                "/documents",
                data={"owner_id": "user-list"},
                files={"file": (name, f"%PDF-1.4\n{name}".encode("utf-8"), "application/pdf")},
            )
            assert create_response.status_code == 201

        # Default list includes all statuses; callers can narrow by status when needed.
        list_response = client.get("/documents")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 2
        assert {item["status"] for item in payload} == {"processing"}

        processing_list_response = client.get("/documents?status=processing")
        assert processing_list_response.status_code == 200
        processing_payload = processing_list_response.json()
        assert len(processing_payload) >= 2
        assert processing_payload[0]["filename"] in {"a.pdf", "b.pdf"}
        assert "llm_metadata" in processing_payload[0]
        assert processing_payload[0]["llm_metadata"] is None
    finally:
        app.dependency_overrides.clear()


def test_list_documents_includes_llm_metadata_when_available() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
        assert get_response.json()["blob_uri"].startswith("processed/")

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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
        ready_document = repository.get(ready_id)
        assert ready_document is not None
        ready_document.status = DocumentStatus.READY
        repository.save(ready_document)

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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
        ready_document = repository.get(ready_id)
        assert ready_document is not None
        ready_document.status = DocumentStatus.READY
        repository.save(ready_document)

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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
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
        assert detail["ocr_text_preview"] is None
        assert detail["ocr_parsed_at"] is None

        history_response = client.get(f"/documents/{doc_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()
        event_types = {event["event_type"] for event in history}
        assert "metadata_changed" in event_types
        assert "tags_added" in event_types

        patch_events = [event for event in history if event["source"] == "api.patch_metadata"]
        assert patch_events
        assert all(event["actor_type"] == "user" for event in patch_events)
        assert all(event["actor_id"] == TEST_USER.id for event in patch_events)
    finally:
        app.dependency_overrides.clear()


def test_parse_document_roundtrip() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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

        detail_response = client.get(f"/documents/{doc_id}/detail")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert "fake-content" in detail_payload["ocr_text_preview"]
        assert detail_payload["ocr_parsed_at"] is not None
    finally:
        app.dependency_overrides.clear()


def test_reprocess_document_requeues_and_sets_processing() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/parse")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
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
        assert get_response.json()["blob_uri"].startswith("processed/")

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
        processing_events = [event for event in history if event["event_type"] == "processing_completed"]
        assert processing_events
        processing_parse = processing_events[0]["changes"]["parse"]
        assert processing_parse["parser"] == "stub-llm-ocr"
        assert processing_parse["text_preview_bytes"] > 0
        assert processing_parse["ocr_process"]["location"] == "remote"
        assert processing_parse["ocr_process"]["engine"] == "llm"
        assert processing_parse["ocr_process"]["method"] == "llm_text"
        assert processing_parse["ocr_process"]["provider"] == "fake"
        assert processing_parse["ocr_process"]["result_size_bytes"] == processing_parse["text_preview_bytes"]
        assert processing_parse["ocr"]["requested_provider"] == "llm"
        assert processing_parse["ocr"]["attempts"]["text_extraction"]["attempted"] is True
        assert processing_parse["ocr"]["attempts"]["llm_text"]["succeeded"] is True
        assert processing_parse["ocr"]["final_text_source"] == "llm_text_ocr"
        metadata_parse = processing_events[0]["changes"]["metadata_parse"]
        assert metadata_parse["provider"] == "fake"
        assert metadata_parse["model"] == "metadata-test-model"

        llm_events = [event for event in history if event["source"] == "api.llm_parse"]
        assert llm_events
        assert all(event["actor_type"] == "user" for event in llm_events)
        assert all(event["actor_id"] == TEST_USER.id for event in llm_events)
    finally:
        app.dependency_overrides.clear()


def test_get_llm_parse_result_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-doc/llm-parse")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_get_document_history_not_found() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

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
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
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


def test_tag_stats_only_include_current_user_documents() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        own_doc_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
            files={"file": ("own.pdf", b"%PDF-1.7\nown", "application/pdf")},
        )
        assert own_doc_response.status_code == 201
        own_doc_id = own_doc_response.json()["id"]
        own_llm = client.post(f"/documents/{own_doc_id}/llm-parse")
        assert own_llm.status_code == 200

        # Create another owner's document directly in repository to simulate cross-user data.
        other_doc_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
            files={"file": ("other.pdf", b"%PDF-1.7\nother", "application/pdf")},
        )
        assert other_doc_response.status_code == 201
        other_doc_id = other_doc_response.json()["id"]
        other_doc = repository.get(other_doc_id)
        assert other_doc is not None
        other_doc.owner_id = "different-user-id"
        repository.save(other_doc)
        other_llm = client.post(f"/documents/{other_doc_id}/llm-parse")
        assert other_llm.status_code == 404

        # Inject other user's metadata directly (avoids auth boundary in endpoint tests).
        repository.save_llm_parse_result(
            LLMParseResult(
                document_id=other_doc_id,
                suggested_title="Other User Doc",
                document_date="2026-03-01",
                correspondent="Other Corp",
                document_type="Statement",
                tags=["PrivateTag"],
                created_correspondent=True,
                created_document_type=True,
                created_tags=["PrivateTag"],
                created_at=datetime.now(UTC),
            )
        )

        tag_stats_response = client.get("/documents/metadata/tag-stats")
        assert tag_stats_response.status_code == 200
        tag_names = {item["tag"] for item in tag_stats_response.json()}
        assert "PrivateTag" not in tag_names
        assert "Credit" in tag_names
        assert "Identity" in tag_names
    finally:
        app.dependency_overrides.clear()


def test_document_type_stats_only_include_current_user_documents() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        client = TestClient(app)
        own_doc_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
            files={"file": ("own.pdf", b"%PDF-1.7\nown", "application/pdf")},
        )
        assert own_doc_response.status_code == 201
        own_doc_id = own_doc_response.json()["id"]
        own_llm = client.post(f"/documents/{own_doc_id}/llm-parse")
        assert own_llm.status_code == 200

        other_doc_response = client.post(
            "/documents",
            data={"owner_id": TEST_USER.id},
            files={"file": ("other.pdf", b"%PDF-1.7\nother", "application/pdf")},
        )
        assert other_doc_response.status_code == 201
        other_doc_id = other_doc_response.json()["id"]
        other_doc = repository.get(other_doc_id)
        assert other_doc is not None
        other_doc.owner_id = "different-user-id"
        repository.save(other_doc)
        other_llm = client.post(f"/documents/{other_doc_id}/llm-parse")
        assert other_llm.status_code == 404

        repository.save_llm_parse_result(
            LLMParseResult(
                document_id=other_doc_id,
                suggested_title="Other User Doc",
                document_date="2026-03-01",
                correspondent="Other Corp",
                document_type="Private Type",
                tags=["PrivateTag"],
                created_correspondent=True,
                created_document_type=True,
                created_tags=["PrivateTag"],
                created_at=datetime.now(UTC),
            )
        )

        type_stats_response = client.get("/documents/metadata/document-type-stats")
        assert type_stats_response.status_code == 200
        type_names = {item["document_type"] for item in type_stats_response.json()}
        assert "Private Type" not in type_names
        assert "Credit Report" in type_names
    finally:
        app.dependency_overrides.clear()


def test_llm_parse_uses_configured_provider_with_injected_fake_provider() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeLLMProvider()

    try:
        repository.save_user_preference(
            UserPreference(
                user_id=TEST_USER.id,
                preferences={
                    "llm_provider": "openai",
                    "llm_api_key": "sk-test",
                    "llm_model": "gpt-4.1-mini",
                },
            )
        )
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("credit.pdf", b"%PDF-1.7\ncredit", "application/pdf")},
        )
        assert create_response.status_code == 201
        document_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{document_id}/llm-parse")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["document_type"] == "Credit Report"
    finally:
        app.dependency_overrides.clear()


def test_llm_parse_requires_user_llm_provider_configuration() -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("needs-llm.pdf", b"%PDF-1.7\nsample", "application/pdf")},
        )
        assert create_response.status_code == 201
        document_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{document_id}/llm-parse")
        assert parse_response.status_code == 400
        assert "Configure an LLM provider in Settings" in parse_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_requires_provider_configuration() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.post("/documents/llm/test", json={})
        assert response.status_code == 400
        assert response.json()["detail"] == "Configure an LLM provider in Settings before running LLM parse."
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_requires_base_url_for_custom_provider() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={"provider": "custom", "api_key": "sk-test"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Custom LLM provider requires a base URL in Settings."
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_rejects_openai_style_key_for_gemini() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={"provider": "gemini", "api_key": "sk-test"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Gemini API keys should not start with sk-. Paste your Google AI Studio API key."
        )
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_accepts_payload_overrides_and_calls_provider() -> None:
    repository = InMemoryDocumentRepository()
    fake_provider = FakeLLMProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com/v1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["provider"] == "openai"
        assert payload["model"] == "gpt-4.1-mini"
        assert fake_provider.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_can_probe_grounded_qa_task() -> None:
    repository = InMemoryDocumentRepository()
    fake_provider = FakeLLMProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "task": "grounded_qa",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com/v1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["provider"] == "openai"
        assert payload["model"] == "gpt-4.1-mini"
        assert fake_provider.calls == 0
        assert fake_provider.tool_calls == 1
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_can_probe_ocr_task() -> None:
    repository = InMemoryDocumentRepository()
    fake_provider = FakeLLMProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "task": "ocr",
                "provider": "openai",
                "model": "gpt-4.1-nano",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com/v1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["provider"] == "openai"
        assert payload["model"] == "gpt-4.1-nano"
        assert fake_provider.calls == 0
        assert fake_provider.ocr_calls == 0
        assert fake_provider.image_ocr_calls == 1
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_custom_task_runs_task_probe(monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    fake_provider = FakeLLMProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    def fail_if_models_endpoint_is_used(*_args, **_kwargs):
        raise AssertionError("custom task tests should run the selected task probe")

    monkeypatch.setattr(llm_connection_test.httpx, "Client", fail_if_models_endpoint_is_used)

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "task": "ocr",
                "provider": "custom",
                "model": "qwen3-0.6b",
                "api_key": "lm-studio",
                "base_url": "http://hyperion.local.zellux.me:1234/v1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["provider"] == "custom"
        assert payload["model"] == "qwen3-0.6b"
        assert fake_provider.ocr_calls == 0
        assert fake_provider.image_ocr_calls == 1
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_ocr_requires_reading_test_image() -> None:
    repository = InMemoryDocumentRepository()

    class FakeTextOnlyOCRProvider(FakeLLMProvider):
        def extract_ocr_text_from_images(
            self,
            *,
            filename: str,
            image_data_urls: list[str],
        ) -> str:
            del filename
            del image_data_urls
            self.image_ocr_calls += 1
            return "I cannot read images, but the text path is available."

    fake_provider = FakeTextOnlyOCRProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "task": "ocr",
                "provider": "custom",
                "model": "qwen3-0.6b",
                "api_key": "lm-studio",
                "base_url": "http://hyperion.local.zellux.me:1234/v1",
            },
        )
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "OCR model did not read the connection test image" in detail
        assert fake_provider.image_ocr_calls == 1
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_uses_models_endpoint_for_custom_provider(monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    captured: dict[str, object] = {"paths": []}

    class FakeModelsClient:
        def __init__(self, *, base_url: str, timeout: float, headers: dict[str, str]) -> None:
            captured["base_url"] = base_url
            captured["timeout"] = timeout
            captured["headers"] = headers

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _traceback) -> None:
            return None

        def get(self, path: str):
            captured["paths"].append(path)

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {"data": [{"id": "qwen3-0.6b"}]}

            return Response()

    monkeypatch.setattr(llm_connection_test.httpx, "Client", FakeModelsClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "provider": "custom",
                "model": "qwen3-0.6b",
                "api_key": "lm-studio",
                "base_url": "http://hyperion.local.zellux.me:1234/v1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["provider"] == "custom"
        assert payload["model"] == "qwen3-0.6b"
        assert captured["base_url"] == "http://hyperion.local.zellux.me:1234/v1"
        assert captured["paths"] == ["/models"]
    finally:
        app.dependency_overrides.clear()


def test_llm_connection_test_includes_provider_response_body_on_failure() -> None:
    repository = InMemoryDocumentRepository()
    fake_provider = FakeFailingLLMProvider()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: fake_provider

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/llm/test",
            json={
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "api_key": "sk-bad",
                "base_url": "https://api.openai.com/v1",
            },
        )
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "LLM API test failed:" in detail
        assert "401 Unauthorized" in detail
        assert "Invalid API key: sk-bad" in detail
        assert "invalid_request_error" in detail
    finally:
        app.dependency_overrides.clear()


def test_local_ocr_status_endpoint_returns_capabilities() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.get("/documents/ocr/local-status")
        assert response.status_code == 200
        payload = response.json()
        assert "available" in payload
        assert "tesseract_available" in payload
        assert "pdftoppm_available" in payload
        assert "detail" in payload
    finally:
        app.dependency_overrides.clear()


def test_parse_endpoint_returns_runtime_error_as_bad_request(monkeypatch) -> None:
    store_dir = Path("local/test-object-store")
    repository = InMemoryDocumentRepository()
    dispatcher = FakeDispatcher()
    storage = LocalStorageAdapter(str(store_dir))
    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[ingestion_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[storage_dependency] = lambda: storage

    def _raise_runtime_error(**kwargs):
        del kwargs
        raise RuntimeError("Local OCR unavailable: install `tesseract`.")

    monkeypatch.setattr(documents_routes, "parse_document_blob", _raise_runtime_error)

    try:
        client = TestClient(app)
        create_response = client.post(
            "/documents",
            files={"file": ("needs-ocr.pdf", b"%PDF-1.7\nsample", "application/pdf")},
        )
        assert create_response.status_code == 201
        document_id = create_response.json()["id"]

        parse_response = client.post(f"/documents/{document_id}/parse")
        assert parse_response.status_code == 400
        assert parse_response.json()["detail"] == "Local OCR unavailable: install `tesseract`."
    finally:
        app.dependency_overrides.clear()
