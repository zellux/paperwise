from typing import Any, Protocol

from paperwise.application.interfaces import CollectionRepository, DocumentStore, ParseResultRepository
from paperwise.application.services.grounded_qa import GroundedQAResult
from paperwise.domain.models import Collection
from paperwise.server.schemas.collections import (
    AskCitationResponse,
    AskResponse,
    CollectionResponse,
    SearchHitResponse,
    SearchResponse,
)


class CollectionResponseRepository(CollectionRepository, Protocol):
    pass


class CollectionSearchResponseRepository(DocumentStore, ParseResultRepository, Protocol):
    pass


def present_collection(
    *,
    collection: Collection,
    document_count: int,
) -> CollectionResponse:
    return CollectionResponse(
        id=collection.id,
        owner_id=collection.owner_id,
        name=collection.name,
        description=collection.description,
        document_count=document_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def present_collection_from_repository(
    *,
    repository: CollectionResponseRepository,
    collection: Collection,
) -> CollectionResponse:
    return present_collection(
        collection=collection,
        document_count=len(repository.list_collection_document_ids(collection.id)),
    )


def present_search_hit(
    *,
    repository: CollectionSearchResponseRepository,
    hit: Any,
) -> SearchHitResponse | None:
    doc_id = hit.chunk.document_id
    document = repository.get(doc_id)
    if document is None:
        return None
    llm = repository.get_llm_parse_result(doc_id)
    title = llm.suggested_title if llm is not None and llm.suggested_title else document.filename
    return SearchHitResponse(
        document_id=doc_id,
        title=title,
        filename=document.filename,
        score=hit.score,
        snippet=hit.chunk.content[:280],
        matched_terms=hit.matched_terms,
        created_at=document.created_at,
        document_type=llm.document_type if llm is not None else None,
        correspondent=llm.correspondent if llm is not None else None,
        tags=list(llm.tags or []) if llm is not None else [],
    )


def present_search_response(
    *,
    repository: CollectionSearchResponseRepository,
    query: str,
    limit: int,
    hits: list[Any],
) -> SearchResponse:
    best_hits_by_doc: dict[str, tuple[Any, float]] = {}
    ordered_doc_ids: list[str] = []
    for hit in hits:
        doc_id = hit.chunk.document_id
        score = float(hit.score)
        current = best_hits_by_doc.get(doc_id)
        if current is None:
            best_hits_by_doc[doc_id] = (hit, score)
            ordered_doc_ids.append(doc_id)
            continue
        if score > current[1]:
            best_hits_by_doc[doc_id] = (hit, score)
    items: list[SearchHitResponse] = []
    for doc_id in ordered_doc_ids:
        item = present_search_hit(
            repository=repository,
            hit=best_hits_by_doc[doc_id][0],
        )
        if item is not None:
            items.append(item)
        if len(items) >= max(1, limit):
            break
    return SearchResponse(query=query, total_hits=len(items), hits=items)


def present_ask_response(result: GroundedQAResult) -> AskResponse:
    return AskResponse(
        question=result.question,
        answer=result.answer,
        insufficient_evidence=result.insufficient_evidence,
        citations=[
            AskCitationResponse(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                title=item.title,
                quote=item.quote,
            )
            for item in result.citations
        ],
        debug=result.debug,
    )
