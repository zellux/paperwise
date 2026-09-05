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
    # Resolve the user's boundary first. Model-supplied filters may only narrow it.
    base_ids = resolve_chat_scope(repository, current_user, scope)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository, current_user=current_user, base_document_ids=base_ids,
        tag_filters=arguments.get("tags", []),
        document_type_filters=arguments.get("document_types", []),
        correspondent_filters=arguments.get("correspondents", []),
        date_from=arguments.get("date_from"), date_to=arguments.get("date_to"),
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
            llm_provider=None,
        )
        contexts = build_qa_contexts(
            repository=repository,
            chunk_hits=hits,
            top_k_chunks=limit,
            max_documents=max_documents,
        )
        contexts = compact_chat_search_contexts(contexts, query)
        selected_ids = scoped_ids if scoped_ids is not None else all_owned_document_ids(repository, current_user)
        return {
            "coverage": {
                **chat_scope_readiness(repository, current_user, selected_ids),
                "retrieved_documents": len({c["document_id"] for c in contexts}),
                "limited": len(hits) > len(contexts) or len(hits) >= limit * 3 or any(c.get("content_truncated") for c in contexts),
                "filters": {key: value for key, value in arguments.items() if key not in {"query", "limit"}},
            },
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
        return {"documents": items, "total_results": len(document_ids), "returned_results": len(items),
                "coverage": {"scope_documents": len(document_ids), "limited": len(items) < len(document_ids),
                             "filters": {key: value for key, value in arguments.items() if key != "limit"}}}
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
        if document is None or document.owner_id != current_user.id or (scoped_ids is not None and document_id not in scoped_ids):
            return {"error": "Document not found."}
        max_chunks = max(1, min(20, int(arguments.get("max_chunks") or 8)))
        metadata = tool_document_item(repository, document_id)
        all_chunks = repository.list_document_chunks(document_id)
        chunks = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": metadata["title"] if metadata else document.filename,
                "content": chunk.content[:2500],
            }
            for chunk in all_chunks[:max_chunks]
        ]
        return {"document": metadata, "chunks": chunks, "total_results": len(chunks),
                "coverage": {"scope_documents": 1, "unready_documents": 0,
                             "limited": len(all_chunks) > len(chunks) or any(len(c.content) > 2500 for c in all_chunks[:max_chunks])}}
    return {"error": f"Unknown tool: {name}"}


def resolve_chat_scope(repository: ChatToolRepository, current_user: User, scope: ChatToolScope) -> list[str] | None:
    return resolve_metadata_scoped_document_ids(
        repository=repository, current_user=current_user, base_document_ids=None,
        tag_filters=scope.tag, document_type_filters=scope.document_type,
        correspondent_filters=scope.correspondent,
        date_from=scope.date_from, date_to=scope.date_to,
    )


def chat_scope_readiness(repository: ChatToolRepository, current_user: User, ids: list[str]) -> dict[str, int]:
    states_fn = getattr(repository, "list_document_index_states", None)
    states = {state.document_id: state.status for state in states_fn(owner_id=current_user.id, document_ids=ids)} if callable(states_fn) and ids else {}
    unready = 0
    for document_id in ids:
        document = repository.get(document_id)
        if document is None or document.status != "ready" or states.get(document_id, "ready") != "ready" or (document_id not in states and not repository.list_document_chunks(document_id)):
            unready += 1
    return {"scope_documents": len(ids), "unready_documents": unready}


def chat_library_summary(repository: ChatToolRepository, current_user: User) -> dict[str, Any]:
    ids = all_owned_document_ids(repository, current_user)
    return {
        **chat_scope_readiness(repository, current_user, ids),
        "tags": taxonomy_stats_payload(repository.list_owner_tag_stats(current_user.id), limit=1000),
        "document_types": taxonomy_stats_payload(repository.list_owner_document_type_stats(current_user.id), limit=1000),
        "correspondents": taxonomy_stats_payload(repository.list_owner_correspondent_stats(current_user.id), limit=1000),
    }
