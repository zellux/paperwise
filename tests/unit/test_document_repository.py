from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from paperwise.domain.models import Document, DocumentStatus, LLMParseResult
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)


def _document(document_id: str, owner_id: str) -> Document:
    return Document(
        id=document_id,
        filename=f"{document_id}.pdf",
        owner_id=owner_id,
        blob_uri=f"incoming/{document_id}.pdf",
        checksum_sha256=document_id,
        content_type="application/pdf",
        size_bytes=123,
        status=DocumentStatus.READY,
        created_at=datetime.now(UTC),
    )


def _processing_document(document_id: str, owner_id: str) -> Document:
    document = _document(document_id, owner_id)
    document.status = DocumentStatus.PROCESSING
    return document


def _llm_result(
    document_id: str,
    document_type: str,
    tags: list[str],
    *,
    correspondent: str = "Bank",
) -> LLMParseResult:
    return LLMParseResult(
        document_id=document_id,
        suggested_title=f"{document_id} title",
        document_date=None,
        correspondent=correspondent,
        document_type=document_type,
        tags=tags,
        created_correspondent=False,
        created_document_type=False,
        created_tags=[],
        created_at=datetime.now(UTC),
    )


def test_owner_taxonomy_stats_are_scoped_to_document_owner() -> None:
    repository = InMemoryDocumentRepository()
    repository.save(_document("owner-a-1", "owner-a"))
    repository.save(_document("owner-a-2", "owner-a"))
    repository.save(_document("owner-b-1", "owner-b"))
    repository.save_llm_parse_result(
        _llm_result("owner-a-1", "invoice", ["tax", "Tax"], correspondent="Bank")
    )
    repository.save_llm_parse_result(
        _llm_result("owner-a-2", "statement", ["finance"], correspondent="Credit Union")
    )
    repository.save_llm_parse_result(
        _llm_result("owner-b-1", "invoice", ["tax"], correspondent="Bank")
    )

    assert repository.list_owner_tag_stats("owner-a") == [("Finance", 1), ("Tax", 1)]
    assert repository.list_owner_document_type_stats("owner-a") == [
        ("Invoice", 1),
        ("Statement", 1),
    ]
    assert repository.list_owner_correspondent_stats("owner-a") == [
        ("Bank", 1),
        ("Credit Union", 1),
    ]


def test_postgres_owner_taxonomy_stats_are_scoped_to_document_owner(tmp_path: Path) -> None:
    repository = PostgresDocumentRepository(f"sqlite:///{tmp_path / 'paperwise.db'}")
    repository.save(_document("owner-a-1", "owner-a"))
    repository.save(_document("owner-a-2", "owner-a"))
    repository.save(_document("owner-b-1", "owner-b"))
    repository.save_llm_parse_result(
        _llm_result("owner-a-1", "invoice", ["tax", "Tax"], correspondent="Bank")
    )
    repository.save_llm_parse_result(
        _llm_result("owner-a-2", "statement", ["finance"], correspondent="Credit Union")
    )
    repository.save_llm_parse_result(
        _llm_result("owner-b-1", "invoice", ["tax"], correspondent="Bank")
    )

    assert repository.list_owner_tag_stats("owner-a") == [("Finance", 1), ("Tax", 1)]
    assert repository.list_owner_document_type_stats("owner-a") == [
        ("Invoice", 1),
        ("Statement", 1),
    ]
    assert repository.list_owner_correspondent_stats("owner-a") == [
        ("Bank", 1),
        ("Credit Union", 1),
    ]


def test_list_owner_documents_with_llm_results_returns_owner_rows() -> None:
    repository = InMemoryDocumentRepository()
    repository.save(_document("owner-a-1", "owner-a"))
    repository.save(_document("owner-b-1", "owner-b"))
    repository.save_llm_parse_result(_llm_result("owner-a-1", "invoice", ["tax"]))
    repository.save_llm_parse_result(_llm_result("owner-b-1", "statement", ["finance"]))

    rows = repository.list_owner_documents_with_llm_results(owner_id="owner-a")

    assert [(document.id, llm_result.document_type if llm_result else None) for document, llm_result in rows] == [
        ("owner-a-1", "invoice")
    ]


def test_list_owner_documents_with_llm_results_filters_by_status() -> None:
    repository = InMemoryDocumentRepository()
    repository.save(_document("owner-a-ready", "owner-a"))
    repository.save(_processing_document("owner-a-processing", "owner-a"))
    repository.save(_processing_document("owner-b-processing", "owner-b"))

    rows = repository.list_owner_documents_with_llm_results(
        owner_id="owner-a",
        statuses={DocumentStatus.PROCESSING},
    )

    assert [document.id for document, _llm_result in rows] == ["owner-a-processing"]


def test_count_owner_documents_by_statuses_is_owner_scoped() -> None:
    repository = InMemoryDocumentRepository()
    repository.save(_processing_document("owner-a-processing", "owner-a"))
    repository.save(_document("owner-a-ready", "owner-a"))
    repository.save(_processing_document("owner-b-processing", "owner-b"))

    count = repository.count_owner_documents_by_statuses(
        owner_id="owner-a",
        statuses={DocumentStatus.RECEIVED, DocumentStatus.PROCESSING, DocumentStatus.FAILED},
    )

    assert count == 1


def test_postgres_repository_adds_starred_column_to_existing_documents_table(tmp_path: Path) -> None:
    db_path = tmp_path / "paperwise-existing.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE documents (
                id VARCHAR(64) PRIMARY KEY,
                filename VARCHAR(1024),
                owner_id VARCHAR(256),
                blob_uri TEXT,
                checksum_sha256 VARCHAR(64),
                content_type VARCHAR(256),
                size_bytes INTEGER,
                status VARCHAR(32),
                created_at DATETIME
            )
            """
        )
        connection.commit()

    repository = PostgresDocumentRepository(f"sqlite:///{db_path}")
    document = _document("star-migration", "owner-star")
    document.starred = True
    repository.save(document)

    loaded = repository.get("star-migration")
    assert loaded is not None
    assert loaded.starred is True
