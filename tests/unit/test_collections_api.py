from datetime import UTC, datetime

from fastapi.testclient import TestClient

from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.domain.models import (
    Document,
    DocumentChunk,
    DocumentChunkSearchHit,
    DocumentStatus,
    LLMParseResult,
    ParseResult,
    User,
)
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.main import app
from paperwise.server.routes.collections import _build_qa_contexts
from paperwise.server.routes.query import _compact_chat_context_content


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

    def rewrite_retrieval_queries(self, *, question: str) -> dict:
        return {
            "queries": [question],
            "must_terms": [],
            "optional_terms": [],
        }


def test_compact_chat_context_keeps_query_centered_excerpt() -> None:
    content = "intro " * 500 + "Height 2 ft 10 in recorded at the visit. " + "footer " * 500

    excerpt, truncated = _compact_chat_context_content(content, "Quincy height")

    assert truncated is True
    assert len(excerpt) < len(content)
    assert "Height 2 ft 10 in" in excerpt
    assert excerpt.startswith("...")
    assert excerpt.endswith("...")


class FakeAnchoredGroundedLLM(FakeGroundedLLM):
    def rewrite_retrieval_queries(self, *, question: str) -> dict:
        del question
        return {
            "queries": ["Quincy height measurement history"],
            "must_terms": ["Quincy", "height", "measurements"],
            "anchor_terms": ["Quincy", "height"],
            "optional_terms": ["cm", "inches"],
        }


class FakeMassRewriteGroundedLLM(FakeGroundedLLM):
    def rewrite_retrieval_queries(self, *, question: str) -> dict:
        del question
        return {
            "queries": ["Quincy weight vital signs", "Quincy body weight lb kg"],
            "must_terms": ["weight"],
            "anchor_terms": ["Quincy", "weight"],
            "optional_terms": ["lb", "kg", "vital signs"],
        }


class FakeSonicRewriteGroundedLLM(FakeGroundedLLM):
    def rewrite_retrieval_queries(self, *, question: str) -> dict:
        del question
        return {
            "queries": [
                "monthly spending on Sonic internet",
                "Sonic internet monthly bill amount",
            ],
            "must_terms": ["Sonic internet", "monthly", "spend"],
            "anchor_terms": ["Sonic internet", "Sonic"],
            "optional_terms": ["cost", "bill", "charges", "payment", "per month", "monthly fee"],
        }


class FakeTimeoutGroundedLLM(FakeGroundedLLM):
    def answer_grounded(self, *, question: str, contexts: list[dict]) -> dict:
        del question
        del contexts
        raise RuntimeError("The read operation timed out")


class FakeToolChatLLM(FakeGroundedLLM):
    def __init__(self) -> None:
        self.calls = 0

    def answer_with_tools(self, *, messages: list[dict], tools: list[dict]) -> dict:
        del tools
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "content": "",
                "llm_total_tokens": 11,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "search_document_chunks",
                        "arguments": '{"query":"Sonic internet amount","tags":["Utilities"],"limit":5}',
                    }
                ],
            }
        tool_payload = {}
        for message in messages:
            if message.get("role") == "tool":
                import json

                tool_payload = json.loads(message.get("content", "{}"))
        results = tool_payload.get("results", [])
        title = results[0].get("title", "the document") if results else "the document"
        return {
            "role": "assistant",
            "content": f"Sonic internet is covered by {title}.",
            "llm_total_tokens": 13,
            "tool_calls": [],
        }


class FakeMetadataToolChatLLM(FakeGroundedLLM):
    def __init__(self) -> None:
        self.calls = 0

    def answer_with_tools(self, *, messages: list[dict], tools: list[dict]) -> dict:
        del tools
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "content": "",
                "llm_total_tokens": 17,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "query_document_metadata",
                        "arguments": '{"document_types":["Invoice"],"limit":10}',
                    }
                ],
            }
        return {
            "role": "assistant",
            "content": "I found the matching invoice metadata.",
            "llm_total_tokens": 19,
            "tool_calls": [],
        }


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
    document_date: str | None = "2026-03-10",
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
            document_date=document_date,
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


def test_chat_queries_all_documents_with_tool_calls() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-sonic",
        owner_id=TEST_USER.id,
        filename="sonic.pdf",
        text_preview="Sonic Internet monthly bill amount due: $54.99.",
        title="Sonic Internet Bill",
        document_type="Invoice",
        tags=["Utilities"],
    )
    _save_document(
        repository,
        doc_id="doc-medical",
        owner_id=TEST_USER.id,
        filename="medical.pdf",
        text_preview="Pediatric visit note with height and weight.",
        title="Visit Note",
        document_type="Visit Note",
        tags=["Medical"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeToolChatLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/query/chat",
            json={
                "messages": [{"role": "user", "content": "How much was Sonic internet?"}],
                "top_k_chunks": 8,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "Sonic Internet Bill" in payload["message"]["content"]
        assert payload["tool_calls"][0]["name"] == "search_document_chunks"
        assert payload["token_usage"]["total_tokens"] == 24
        assert payload["token_usage"]["llm_requests"] == 2
        assert payload["citations"]
        assert payload["citations"][0]["document_id"] == "doc-sonic"
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_reports_tool_progress() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-sonic",
        owner_id=TEST_USER.id,
        filename="sonic.pdf",
        text_preview="Sonic Internet monthly bill amount due: $54.99.",
        title="Sonic Internet Bill",
        document_type="Invoice",
        tags=["Utilities"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeToolChatLLM()

    try:
        client = TestClient(app)
        with client.stream(
            "POST",
            "/query/chat/stream",
            json={
                "messages": [{"role": "user", "content": "How much was Sonic internet?"}],
                "top_k_chunks": 8,
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
        assert "event: status" in body
        assert "event: tool_call" in body
        assert "event: tool_result" in body
        assert "event: token_usage" in body
        assert '"total_tokens": 24' in body
        assert "event: final" in body
    finally:
        app.dependency_overrides.clear()


def test_chat_metadata_tool_scans_all_owned_documents() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-invoice",
        owner_id=TEST_USER.id,
        filename="invoice.pdf",
        text_preview="Invoice amount details.",
        title="Invoice Doc",
        document_type="Invoice",
        tags=["Finance"],
    )
    _save_document(
        repository,
        doc_id="doc-contract",
        owner_id=TEST_USER.id,
        filename="contract.pdf",
        text_preview="Service agreement details.",
        title="Contract Doc",
        document_type="Contract",
        tags=["Legal"],
    )
    _save_document(
        repository,
        doc_id="doc-other-owner",
        owner_id="other-user",
        filename="other.pdf",
        text_preview="Invoice amount details.",
        title="Other Invoice",
        document_type="Invoice",
        tags=["Finance"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeMetadataToolChatLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/query/chat",
            json={
                "messages": [{"role": "user", "content": "Which invoices do I have?"}],
                "debug": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["tool_calls"][0]["name"] == "query_document_metadata"
        assert payload["token_usage"]["total_tokens"] == 36
        documents = payload["debug"]["steps"][0]["result"]["documents"]
        assert [item["document_id"] for item in documents] == ["doc-invoice"]
    finally:
        app.dependency_overrides.clear()


def test_chat_returns_clean_error_for_provider_without_tool_chat() -> None:
    repository = InMemoryDocumentRepository()

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/query/chat",
            json={"messages": [{"role": "user", "content": "What documents do I have?"}]},
        )
        assert response.status_code == 400
        assert "does not support conversational tool use" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_global_ask_query_expansion_handles_measurement_wording() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-vitals",
        owner_id=TEST_USER.id,
        filename="visit-note.pdf",
        text_preview="Vital signs: Weight 45 lb. Height 120 cm. Follow-up in 6 months.",
        title="Pediatric Visit Note",
        document_type="Visit Note",
        tags=["Medical"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeMassRewriteGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "List measurement of Quincy mass",
                "top_k_chunks": 8,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["insufficient_evidence"] is False
        assert payload["citations"]
        assert payload["citations"][0]["document_id"] == "doc-vitals"
    finally:
        app.dependency_overrides.clear()


def test_global_ask_returns_debug_payload_when_enabled() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-debug",
        owner_id=TEST_USER.id,
        filename="debug-note.pdf",
        text_preview="Weight 32 lb and height 98 cm for Quincy.",
        title="Debug Visit Note",
        document_type="Visit Note",
        tags=["Medical"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "List measurement of Quincy weight",
                "top_k_chunks": 8,
                "debug": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("debug"), dict)
        debug_payload = payload["debug"]
        assert "retrieval" in debug_payload
        assert "sources_sent_to_llm" in debug_payload
        assert isinstance(debug_payload["sources_sent_to_llm"], list)
        assert debug_payload["sources_sent_to_llm"]
    finally:
        app.dependency_overrides.clear()


def test_global_ask_anchor_filter_prefers_chunks_with_must_terms() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-relevant",
        owner_id=TEST_USER.id,
        filename="visit-note.pdf",
        text_preview="Quincy height 110 cm at visit one. Quincy height 115 cm at visit two.",
        title="Quincy Visit Note",
        document_type="Visit Note",
        tags=["Medical"],
    )
    _save_document(
        repository,
        doc_id="doc-noise",
        owner_id=TEST_USER.id,
        filename="credit.pdf",
        text_preview="Account history and balance records over time with no data and no data.",
        title="Experian Credit Report",
        document_type="Credit Report",
        tags=["Finance"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeAnchoredGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "History of measurements of Quincy's height",
                "top_k_chunks": 8,
                "debug": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["citations"]
        assert payload["citations"][0]["document_id"] == "doc-relevant"
        debug_payload = payload["debug"]
        assert debug_payload["retrieval"]["strong_must_terms"] == ["quincy", "height"]
        assert debug_payload["sources_sent_to_llm"]
        source_doc_ids = {item["document_id"] for item in debug_payload["sources_sent_to_llm"]}
        assert source_doc_ids == {"doc-relevant"}
    finally:
        app.dependency_overrides.clear()


def test_build_qa_contexts_limits_unique_documents() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-a",
        owner_id=TEST_USER.id,
        filename="doc-a.pdf",
        text_preview="Doc A text with Quincy weight information.",
        title="Doc A",
    )
    _save_document(
        repository,
        doc_id="doc-b",
        owner_id=TEST_USER.id,
        filename="doc-b.pdf",
        text_preview="Doc B text with Quincy weight trend.",
        title="Doc B",
    )

    now = datetime.now(UTC)
    chunk_hits = [
        DocumentChunkSearchHit(
            chunk=DocumentChunk(
                id="doc-a:0",
                document_id="doc-a",
                owner_id=TEST_USER.id,
                chunk_index=0,
                content="Doc A chunk 0",
                token_count=4,
                created_at=now,
            ),
            score=0.98,
            matched_terms=[],
        ),
        DocumentChunkSearchHit(
            chunk=DocumentChunk(
                id="doc-b:0",
                document_id="doc-b",
                owner_id=TEST_USER.id,
                chunk_index=0,
                content="Doc B chunk 0",
                token_count=4,
                created_at=now,
            ),
            score=0.97,
            matched_terms=[],
        ),
        DocumentChunkSearchHit(
            chunk=DocumentChunk(
                id="doc-a:1",
                document_id="doc-a",
                owner_id=TEST_USER.id,
                chunk_index=1,
                content="Doc A chunk 1",
                token_count=4,
                created_at=now,
            ),
            score=0.96,
            matched_terms=[],
        ),
    ]

    contexts = _build_qa_contexts(
        repository=repository,
        chunk_hits=chunk_hits,
        top_k_chunks=10,
        max_documents=1,
    )

    selected_doc_ids = {item["document_id"] for item in contexts}
    assert selected_doc_ids == {"doc-a"}
    assert len(contexts) == 2


def test_global_ask_prefers_anchor_entity_over_generic_monthly_terms() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-sonic",
        owner_id=TEST_USER.id,
        filename="sonic.pdf",
        text_preview=(
            "Sonic Internet monthly bill amount due: $54.99. "
            "Monthly service charge and payment confirmation."
        ),
        title="Sonic Internet Bill",
        document_type="Invoice",
        tags=["Utilities"],
    )
    _save_document(
        repository,
        doc_id="doc-fed",
        owner_id=TEST_USER.id,
        filename="fed.pdf",
        text_preview=(
            "Federal Reserve statement with monthly cap per month and payment operations. "
            "Monthly roll over and payment mechanics."
        ),
        title="Federal Reserve Monetary Policy Statement",
        document_type="Statement",
        tags=["Finance"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeSonicRewriteGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "how much paid monthly for Sonic internet",
                "top_k_chunks": 8,
                "debug": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        debug_payload = payload["debug"]
        assert debug_payload["retrieval"]["strong_must_terms"] == ["sonic internet", "sonic", "internet"]
        assert debug_payload["retrieval"]["anchor_filter_applied"] is True
        source_doc_ids = {item["document_id"] for item in debug_payload["sources_sent_to_llm"]}
        assert "doc-sonic" in source_doc_ids
    finally:
        app.dependency_overrides.clear()


def test_global_ask_timeout_returns_clean_gateway_timeout_message() -> None:
    repository = InMemoryDocumentRepository()
    _save_document(
        repository,
        doc_id="doc-timeout",
        owner_id=TEST_USER.id,
        filename="timeout.pdf",
        text_preview="Sonic internet invoice amount due.",
        title="Timeout Doc",
        document_type="Invoice",
        tags=["Utilities"],
    )

    app.dependency_overrides[document_repository_dependency] = lambda: repository
    app.dependency_overrides[current_user_dependency] = lambda: TEST_USER
    app.dependency_overrides[llm_provider_dependency] = lambda: FakeTimeoutGroundedLLM()

    try:
        client = TestClient(app)
        response = client.post(
            "/collections/ask",
            json={
                "question": "How much did I spend on Sonic internet?",
                "top_k_chunks": 8,
            },
        )
        assert response.status_code == 504
        detail = str(response.json().get("detail", ""))
        assert "timed out" in detail.lower()
        assert "incomplete" in detail.lower()
    finally:
        app.dependency_overrides.clear()
