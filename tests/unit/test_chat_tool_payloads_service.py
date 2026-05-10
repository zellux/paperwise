from datetime import UTC, datetime

from paperwise.application.services.chat_tool_payloads import (
    taxonomy_counts_payload,
    taxonomy_stats_payload,
    tool_document_item,
)
from paperwise.domain.models import Document, DocumentStatus, LLMParseResult
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository


def test_tool_document_item_includes_llm_metadata_when_available() -> None:
    repository = InMemoryDocumentRepository()
    now = datetime.now(UTC)
    document = Document(
        id="doc-tool",
        filename="scan.pdf",
        owner_id="owner",
        blob_uri="incoming/scan.pdf",
        checksum_sha256="abc",
        content_type="application/pdf",
        size_bytes=100,
        status=DocumentStatus.READY,
        created_at=now,
    )
    repository.save(document)
    repository.save_llm_parse_result(
        LLMParseResult(
            document_id=document.id,
            suggested_title="Tax Notice",
            document_date="2026-05-01",
            correspondent="IRS",
            document_type="Notice",
            tags=["Tax"],
            created_correspondent=False,
            created_document_type=False,
            created_tags=[],
            created_at=now,
        )
    )

    assert tool_document_item(repository, document.id) == {
        "document_id": "doc-tool",
        "filename": "scan.pdf",
        "title": "Tax Notice",
        "document_date": "2026-05-01",
        "document_type": "Notice",
        "correspondent": "IRS",
        "tags": ["Tax"],
        "created_at": now.isoformat(),
    }


def test_taxonomy_payloads_limit_and_sort_counts() -> None:
    assert taxonomy_stats_payload([("Tax", 3), ("Finance", 2)], limit=1) == [
        {"name": "Tax", "document_count": 3}
    ]
    assert taxonomy_counts_payload({"Finance": 2, "Tax": 3, "Alpha": 3}) == [
        {"name": "Alpha", "document_count": 3},
        {"name": "Tax", "document_count": 3},
        {"name": "Finance", "document_count": 2},
    ]
