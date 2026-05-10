from dataclasses import dataclass, field
from typing import Any, Protocol

from paperwise.application.interfaces import (
    DocumentChunkRepository,
    DocumentStore,
    LLMProvider,
    ParseResultRepository,
    TaxonomyRepository,
)
from paperwise.application.services.chat_contexts import compact_chat_search_contexts
from paperwise.application.services.chat_tool_payloads import (
    taxonomy_counts_payload,
    taxonomy_stats_payload,
    tool_document_item,
)
from paperwise.application.services.document_scope import all_owned_document_ids
from paperwise.application.services.grounded_qa import (
    build_qa_contexts,
    resolve_metadata_scoped_document_ids,
    search_document_chunks_multi_query,
)
from paperwise.domain.models import User


class ChatToolRepository(
    DocumentStore,
    ParseResultRepository,
    TaxonomyRepository,
    DocumentChunkRepository,
    Protocol,
):
    pass


@dataclass(frozen=True)
class ChatToolScope:
    tag: list[str] = field(default_factory=list)
    document_type: list[str] = field(default_factory=list)
    correspondent: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None


def execute_chat_tool(
    *,
    repository: ChatToolRepository,
    llm_provider: LLMProvider,
    current_user: User,
    scope: ChatToolScope,
    top_k_chunks: int,
    max_documents: int,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    merged_filters = _merge_tool_filters(scope, arguments)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=merged_filters["tag"],
        document_type_filters=merged_filters["document_type"],
        correspondent_filters=merged_filters["correspondent"],
        date_from=merged_filters["date_from"],
        date_to=merged_filters["date_to"],
        title_query=str(arguments.get("title_query") or ""),
    )
    if name == "search_document_chunks":
        query = " ".join(str(arguments.get("query") or "").split()).strip()
        limit = max(1, min(60, int(arguments.get("limit") or top_k_chunks)))
        hits = search_document_chunks_multi_query(
            repository=repository,
            owner_id=current_user.id,
            query=query,
            limit=max(limit * 3, limit),
            document_ids=scoped_ids,
            llm_provider=llm_provider,
        )
        contexts = build_qa_contexts(
            repository=repository,
            chunk_hits=hits,
            top_k_chunks=limit,
            max_documents=max_documents,
        )
        contexts = compact_chat_search_contexts(contexts, query)
        return {
            "results": contexts,
            "total_results": len(contexts),
            "scope_document_count": len(scoped_ids) if scoped_ids is not None else None,
        }
    if name == "query_document_metadata":
        limit = max(1, min(100, int(arguments.get("limit") or 25)))
        document_ids = scoped_ids if scoped_ids is not None else all_owned_document_ids(repository, current_user)
        items = []
        for document_id in document_ids[:limit]:
            item = tool_document_item(repository, document_id)
            if item is not None:
                items.append(item)
        return {"documents": items, "total_results": len(document_ids), "returned_results": len(items)}
    if name == "summarize_taxonomy":
        if scoped_ids is None:
            document_ids = all_owned_document_ids(repository, current_user)
            return {
                "document_count": len(document_ids),
                "tags": taxonomy_stats_payload(repository.list_owner_tag_stats(current_user.id)),
                "document_types": taxonomy_stats_payload(
                    repository.list_owner_document_type_stats(current_user.id)
                ),
                "correspondents": taxonomy_stats_payload(
                    repository.list_owner_correspondent_stats(current_user.id)
                ),
            }
        document_ids = scoped_ids
        tag_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        correspondent_counts: dict[str, int] = {}
        for document_id in document_ids:
            llm = repository.get_llm_parse_result(document_id)
            if llm is None:
                continue
            for tag in llm.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            type_counts[llm.document_type] = type_counts.get(llm.document_type, 0) + 1
            correspondent_counts[llm.correspondent] = correspondent_counts.get(llm.correspondent, 0) + 1

        return {
            "document_count": len(document_ids),
            "tags": taxonomy_counts_payload(tag_counts),
            "document_types": taxonomy_counts_payload(type_counts),
            "correspondents": taxonomy_counts_payload(correspondent_counts),
        }
    if name == "get_document_context":
        document_id = str(arguments.get("document_id") or "").strip()
        document = repository.get(document_id)
        if document is None or document.owner_id != current_user.id:
            return {"error": "Document not found."}
        max_chunks = max(1, min(20, int(arguments.get("max_chunks") or 8)))
        metadata = tool_document_item(repository, document_id)
        chunks = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": metadata["title"] if metadata else document.filename,
                "content": chunk.content[:2500],
            }
            for chunk in repository.list_document_chunks(document_id)[:max_chunks]
        ]
        return {"document": metadata, "chunks": chunks, "total_results": len(chunks)}
    return {"error": f"Unknown tool: {name}"}


def _merge_tool_filters(scope: ChatToolScope, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag": list(scope.tag or []) + [str(item) for item in arguments.get("tags", []) if str(item).strip()],
        "document_type": list(scope.document_type or [])
        + [str(item) for item in arguments.get("document_types", []) if str(item).strip()],
        "correspondent": list(scope.correspondent or [])
        + [str(item) for item in arguments.get("correspondents", []) if str(item).strip()],
        "date_from": arguments.get("date_from") or scope.date_from,
        "date_to": arguments.get("date_to") or scope.date_to,
    }
