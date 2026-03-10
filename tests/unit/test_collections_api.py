from datetime import UTC, datetime

from fastapi.testclient import TestClient

from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult, User
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.main import app


TEST_USER = User(
    id="user-123",
    email="user-123@example.com",
    full_name="User Test",
    password_hash="pbkdf2_sha256$1$aa$bb",
    is_active=True,
    created_at=datetime.now(UTC),
)


class FakeGroundedLLM:
    def answer_grounded(self, *, question: str, contexts: list[dict]) -> dict:
        del question
        first = contexts[0] if contexts else {}
        return {
            "answer": "Grounded answer from context.",
            "insufficient_evidence": False,
            "citations": [
                {
                    "chunk_id": first.get("chunk_id", ""),
                    "document_id": first.get("document_id", ""),
                    "title": first.get("title", ""),
                    "quote": str(first.get("content", ""))[:120],
                }
            ],
        }

    def suggest_metadata(self, **kwargs):  # pragma: no cover - unused in this test
        raise RuntimeError("unused")

    def extract_ocr_text(self, **kwargs):  # pragma: no cover - unused in this test
        raise RuntimeError("unused")


def _save_document(
    repository: InMemoryDocumentRepository,
    *,
    doc_id: str,
    owner_id: str,
    filename: str,
    text_preview: str,
    title: str,
    document_type: str = "Memo",
    tags: list[str] | None = None,
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
            document_type=document_type,
            tags=list(tags or ["Research"]),
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


def test_ask_collection_uses_scoped_chunks_only() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-a",
        owner_id=TEST_USER.id,
        filename="doc-a.pdf",
        text_preview="Alpha topic details around indexing and retrieval.",
        title="Alpha Doc",
    )
    _save_document(
        repository,
        doc_id="doc-b",
        owner_id=TEST_USER.id,
        filename="doc-b.pdf",
        text_preview="Beta topic details around security and access controls.",
        title="Beta Doc",
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeGroundedLLM()

    try:
        client = TestClient(app)
        create_response = client.post(
            "/collections",
            json={"name": "Alpha Collection", "description": "Scoped QA"},
        )
        assert create_response.status_code == 201
        collection_id = create_response.json()["id"]
        add_response = client.post(
            f"/collections/{collection_id}/documents",
            json={"document_ids": ["doc-a"]},
        )
        assert add_response.status_code == 200

        ask_response = client.post(
            f"/collections/{collection_id}/ask",
            json={"question": "What does alpha say about indexing?"},
        )
        assert ask_response.status_code == 200
        payload = ask_response.json()
        assert payload["insufficient_evidence"] is False
        assert payload["citations"]
        assert payload["citations"][0]["document_id"] == "doc-a"
    finally:
        app.dependency_overrides.clear()


def test_global_search_supports_tag_and_document_type_filters_without_collection() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-finance",
        owner_id=TEST_USER.id,
        filename="finance.pdf",
        text_preview="Annual statement with account balances and transactions.",
        title="Finance Statement",
        document_type="Statement",
        tags=["Finance"],
    )
    _save_document(
        repository,
        doc_id="doc-medical",
        owner_id=TEST_USER.id,
        filename="medical.pdf",
        text_preview="Lab report and treatment notes for pediatric visit.",
        title="Medical Report",
        document_type="Report",
        tags=["Medical"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/search",
            json={
                "query": "report",
                "limit": 10,
                "tag": ["Medical"],
                "document_type": ["Report"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_hits"] == 1
        assert payload["hits"][0]["document_id"] == "doc-medical"
    finally:
        app.dependency_overrides.clear()


def test_global_ask_supports_tag_and_document_type_filters_without_collection() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-contract",
        owner_id=TEST_USER.id,
        filename="contract.pdf",
        text_preview="Service agreement terms and renewal clauses.",
        title="Service Contract",
        document_type="Contract",
        tags=["Legal"],
    )
    _save_document(
        repository,
        doc_id="doc-invoice",
        owner_id=TEST_USER.id,
        filename="invoice.pdf",
        text_preview="Invoice items and payable amount details.",
        title="Invoice Doc",
        document_type="Invoice",
        tags=["Finance"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "What do the terms say?",
                "top_k_chunks": 10,
                "tag": ["Legal"],
                "document_type": ["Contract"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["insufficient_evidence"] is False
        assert payload["citations"]
        assert payload["citations"][0]["document_id"] == "doc-contract"
    finally:
        app.dependency_overrides.clear()
