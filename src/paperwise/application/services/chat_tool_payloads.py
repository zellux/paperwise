from typing import Any
from typing import Protocol

from paperwise.application.interfaces import DocumentStore, ParseResultRepository


class ToolDocumentRepository(DocumentStore, ParseResultRepository, Protocol):
    """Repository surface needed to build chat tool document payloads."""


def tool_document_item(repository: ToolDocumentRepository, document_id: str) -> dict[str, Any] | None:
    document = repository.get(document_id)
    if document is None:
        return None
    llm = repository.get_llm_parse_result(document_id)
    return {
        "document_id": document.id,
        "filename": document.filename,
        "title": llm.suggested_title if llm is not None and llm.suggested_title else document.filename,
        "document_date": llm.document_date if llm is not None else None,
        "document_type": llm.document_type if llm is not None else None,
        "correspondent": llm.correspondent if llm is not None else None,
        "tags": list(llm.tags or []) if llm is not None else [],
        "created_at": document.created_at.isoformat(),
    }


def taxonomy_stats_payload(items: list[tuple[str, int]], *, limit: int = 30) -> list[dict[str, Any]]:
    return [
        {"name": item_name, "document_count": count}
        for item_name, count in items[:limit]
    ]


def taxonomy_counts_payload(counts: dict[str, int], *, limit: int = 30) -> list[dict[str, Any]]:
    return taxonomy_stats_payload(
        sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold())),
        limit=limit,
    )
