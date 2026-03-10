from datetime import UTC, datetime

from fastapi.testclient import TestClient

from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult, User
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.dependencies import current_user_dependency, document_repository_dependency
from paperwise.server.main import app


TEST_USER = User(
    id="user-123",
    email="user-123@example.com",
    full_name="User Test",
    password_hash="pbkdf2_sha256$1$aa$bb",
    is_active=True,
    created_at=datetime.now(UTC),
)


def _save_document(
    repository: InMemoryDocumentRepository,
    *,
    doc_id: str,
    owner_id: str,
    filename: str,
    text_preview: str,
    title: str,
) -> None:
    now = datetime.now(UTC)
    repository.save(
        Document(
            id=doc_id,
            filename=filename,
            owner_id=owner_id,
            blob_uri=f"processed/{doc_id}/{filename}",
            checksum_sha256=f"sha-{doc_id}",
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.READY,
            created_at=now,
        )
    )
    repository.save_parse_result(
        ParseResult(
            document_id=doc_id,
            parser="stub-local",
            status="parsed",
            size_bytes=100,
            page_count=1,
            text_preview=text_preview,
            created_at=now,
        )
    )
    parse_result = repository.get_parse_result(doc_id)
    document = repository.get(doc_id)
    assert parse_result is not None
    assert document is not None
    index_document_chunks(repository=repository, document=document, parse_result=parse_result)
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=doc_id,
            suggested_title=title,
            document_date="2026-03-10",
            correspondent="Example Corp",
            document_type="Memo",
            tags=["Research"],
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=now,
        )
    )


def test_collection_scoped_search_returns_only_collection_docs() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-1",
        owner_id=TEST_USER.id,
        filename="doc-1.pdf",
        text_preview="Neural indexing notes and retrieval quality benchmarks.",
        title="Neural Indexing Notes",
    )
    _save_document(
        repository,
        doc_id="doc-2",
        owner_id=TEST_USER.id,
        filename="doc-2.pdf",
        text_preview="Neural search architecture with collection-level ranking.",
        title="Search Architecture",
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)

        create_response = client.post(
            "/collections",
            json={"name": "RAG Research", "description": "Scoped docs"},
        )
        assert create_response.status_code == 201
        collection_id = create_response.json()["id"]

        add_response = client.post(
            f"/collections/{collection_id}/documents",
            json={"document_ids": ["doc-1"]},
        )
        assert add_response.status_code == 200
        assert add_response.json()["document_ids"] == ["doc-1"]

        scoped_search = client.post(
            f"/collections/{collection_id}/search",
            json={"query": "neural", "limit": 10},
        )
        assert scoped_search.status_code == 200
        scoped_payload = scoped_search.json()
        assert scoped_payload["total_hits"] == 1
        assert scoped_payload["hits"][0]["document_id"] == "doc-1"

        global_search = client.post(
            "/collections/search",
            json={"query": "neural", "limit": 10},
        )
        assert global_search.status_code == 200
        global_ids = {hit["document_id"] for hit in global_search.json()["hits"]}
        assert global_ids == {"doc-1", "doc-2"}
    finally:
        app.dependency_overrides.clear()


def test_collection_rejects_documents_not_owned_by_user() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-owned",
        owner_id="another-user",
        filename="doc-owned.pdf",
        text_preview="Private content.",
        title="Private",
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        create_response = client.post(
            "/collections",
            json={"name": "Private", "description": "Test"},
        )
        assert create_response.status_code == 201
        collection_id = create_response.json()["id"]

        add_response = client.post(
            f"/collections/{collection_id}/documents",
            json={"document_ids": ["doc-owned"]},
        )
        assert add_response.status_code == 400
        assert "Invalid document for collection" in add_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
