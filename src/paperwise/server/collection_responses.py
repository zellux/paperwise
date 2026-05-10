from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from paperwise.application.interfaces import CollectionRepository, DocumentStore, ParseResultRepository
from paperwise.domain.models import Collection


class CollectionResponseRepository(CollectionRepository, Protocol):
    pass


class CollectionSearchResponseRepository(DocumentStore, ParseResultRepository, Protocol):
    pass


class CollectionResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    document_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        *,
        collection: Collection,
        document_count: int,
    ) -> "CollectionResponse":
        return cls(
            id=collection.id,
            owner_id=collection.owner_id,
            name=collection.name,
            description=collection.description,
            document_count=document_count,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )

    @classmethod
    def from_repository(
        cls,
        *,
        repository: CollectionResponseRepository,
        collection: Collection,
    ) -> "CollectionResponse":
        return cls.from_domain(
            collection=collection,
            document_count=len(repository.list_collection_document_ids(collection.id)),
        )


class CollectionDocumentIdsResponse(BaseModel):
    collection_id: str
    document_ids: list[str]


class SearchHitResponse(BaseModel):
    document_id: str
    title: str
    filename: str
    score: float
    snippet: str
    matched_terms: list[str]
    created_at: datetime
    document_type: str | None = None
    correspondent: str | None = None
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_chunk_hit(
        cls,
        *,
        repository: CollectionSearchResponseRepository,
        hit: Any,
    ) -> "SearchHitResponse | None":
        doc_id = hit.chunk.document_id
        document = repository.get(doc_id)
        if document is None:
            return None
        llm = repository.get_llm_parse_result(doc_id)
        title = llm.suggested_title if llm is not None and llm.suggested_title else document.filename
        return cls(
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


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[SearchHitResponse]

    @classmethod
    def from_chunk_hits(
        cls,
        *,
        repository: CollectionSearchResponseRepository,
        query: str,
        limit: int,
        hits: list[Any],
    ) -> "SearchResponse":
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
            item = SearchHitResponse.from_chunk_hit(
                repository=repository,
                hit=best_hits_by_doc[doc_id][0],
            )
            if item is not None:
                items.append(item)
            if len(items) >= max(1, limit):
                break
        return cls(query=query, total_hits=len(items), hits=items)


class AskCitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    quote: str


class AskResponse(BaseModel):
    question: str
    answer: str
    insufficient_evidence: bool
    citations: list[AskCitationResponse]
    debug: dict[str, Any] | None = None
