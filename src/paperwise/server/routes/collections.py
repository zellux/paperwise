from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.grounded_qa import (
    build_qa_contexts,
    is_timeout_error,
    resolve_metadata_scoped_document_ids,
    search_document_chunks_multi_query,
)
from paperwise.application.services.llm_preferences import LLM_TASK_GROUNDED_QA
from paperwise.domain.models import Collection, User
from paperwise.infrastructure.llm.debug_log import log_llm_exchange
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.collection_access import get_collection_or_404
from paperwise.server.llm_provider import resolve_http_llm_provider_for_user

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2000)


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
        repository: DocumentRepository,
        collection: Collection,
    ) -> "CollectionResponse":
        return cls.from_domain(
            collection=collection,
            document_count=len(repository.list_collection_document_ids(collection.id)),
        )


class CollectionDocumentsRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class CollectionDocumentIdsResponse(BaseModel):
    collection_id: str
    document_ids: list[str]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    tag: list[str] = Field(default_factory=list)
    document_type: list[str] = Field(default_factory=list)


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
        repository: DocumentRepository,
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
        repository: DocumentRepository,
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


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k_chunks: int = Field(default=18, ge=3, le=60)
    max_documents: int = Field(default=12, ge=1, le=50)
    tag: list[str] = Field(default_factory=list)
    document_type: list[str] = Field(default_factory=list)
    debug: bool = False


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


def _ask_grounded(
    *,
    repository: DocumentRepository,
    llm_provider: LLMProvider,
    owner_id: str,
    question: str,
    top_k_chunks: int,
    max_documents: int,
    document_ids: list[str] | None,
    debug_scope: dict[str, object] | None = None,
    debug_enabled: bool = False,
) -> AskResponse:
    retrieval_debug: dict[str, object] = {}
    chunk_hits = search_document_chunks_multi_query(
        repository=repository,
        owner_id=owner_id,
        query=question,
        limit=max(top_k_chunks * 3, top_k_chunks),
        document_ids=document_ids,
        llm_provider=llm_provider,
        debug=retrieval_debug,
    )
    contexts = build_qa_contexts(
        repository=repository,
        chunk_hits=chunk_hits,
        top_k_chunks=top_k_chunks,
        max_documents=max_documents,
    )
    context_debug = [
        {
            "chunk_id": ctx.get("chunk_id"),
            "document_id": ctx.get("document_id"),
            "title": ctx.get("title"),
            "content_len": len(str(ctx.get("content", ""))),
            "content_preview": str(ctx.get("content", ""))[:800],
        }
        for ctx in contexts
    ]

    request_debug = {
        "owner_id": owner_id,
        "question": question,
        "top_k_chunks": top_k_chunks,
        "max_documents": max_documents,
        "scope": debug_scope or {},
        "retrieval": retrieval_debug,
        "selected_contexts": context_debug,
    }
    response_debug: dict[str, Any] = {}
    if not contexts:
        response_debug = {
            "answer": "Not enough evidence in the selected documents.",
            "insufficient_evidence": True,
            "citations": [],
        }
        log_llm_exchange(
            provider="grounded_qa",
            endpoint="/collections/ask",
            request_payload=request_debug,
            response_status=200,
            response_payload=response_debug,
        )
        return AskResponse(
            question=question,
            answer="Not enough evidence in the selected documents.",
            insufficient_evidence=True,
            citations=[],
            debug=(
                {
                    "scope": request_debug.get("scope"),
                    "retrieval": request_debug.get("retrieval"),
                    "sources_sent_to_llm": request_debug.get("selected_contexts"),
                    "result": response_debug,
                }
                if debug_enabled
                else None
            ),
        )

    try:
        llm_payload = llm_provider.answer_grounded(
            question=question,
            contexts=contexts,
        )
    except Exception as exc:
        if is_timeout_error(exc):
            message = (
                "The LLM request timed out before completion. "
                "Results may be incomplete. Please retry, reduce scope, or lower context limits in Settings."
            )
            log_llm_exchange(
                provider="grounded_qa",
                endpoint="/collections/ask",
                request_payload=request_debug,
                response_status=504,
                response_payload={"detail": message},
                error=str(exc),
            )
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=message) from exc
        raise
    citations: list[AskCitationResponse] = []
    by_chunk = {ctx["chunk_id"]: ctx for ctx in contexts}
    for citation in llm_payload.get("citations", []) if isinstance(llm_payload, dict) else []:
        chunk_id = str(citation.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id not in by_chunk:
            continue
        context = by_chunk[chunk_id]
        citations.append(
            AskCitationResponse(
                chunk_id=chunk_id,
                document_id=context["document_id"],
                title=context["title"],
                quote=str(citation.get("quote", "")).strip() or context["content"][:200],
            )
        )

    answer = str(llm_payload.get("answer", "")).strip() if isinstance(llm_payload, dict) else ""
    insufficient = bool(llm_payload.get("insufficient_evidence", False)) if isinstance(llm_payload, dict) else True
    if not answer:
        answer = "Not enough evidence in the selected documents."
        insufficient = True
    if not citations and not insufficient:
        insufficient = True
        answer = "Not enough evidence in the selected documents."
    response_payload = AskResponse(
        question=question,
        answer=answer,
        insufficient_evidence=insufficient,
        citations=citations,
    )
    response_debug = {
        "answer": response_payload.answer,
        "insufficient_evidence": response_payload.insufficient_evidence,
        "citation_count": len(response_payload.citations),
        "citations": [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "title": item.title,
                "quote_len": len(item.quote),
            }
            for item in response_payload.citations
        ],
    }
    log_llm_exchange(
        provider="grounded_qa",
        endpoint="/collections/ask",
        request_payload=request_debug,
        response_status=200,
        response_payload=response_debug,
    )
    response_payload.debug = (
        {
            "scope": request_debug.get("scope"),
            "retrieval": request_debug.get("retrieval"),
            "sources_sent_to_llm": request_debug.get("selected_contexts"),
            "result": response_debug,
        }
        if debug_enabled
        else None
    )
    return response_payload


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection_endpoint(
    payload: CollectionCreateRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    now = datetime.now(UTC)
    collection = Collection(
        id=str(uuid4()),
        owner_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        created_at=now,
        updated_at=now,
    )
    repository.create_collection(collection)
    return CollectionResponse.from_repository(repository=repository, collection=collection)


@router.get("", response_model=list[CollectionResponse])
def list_collections_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[CollectionResponse]:
    collections = repository.list_collections(current_user.id)
    return [CollectionResponse.from_repository(repository=repository, collection=item) for item in collections]


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    collection = get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return CollectionResponse.from_repository(repository=repository, collection=collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    repository.delete_collection(collection_id)


@router.get("/{collection_id}/documents", response_model=CollectionDocumentIdsResponse)
def list_collection_documents_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.post("/{collection_id}/documents", response_model=CollectionDocumentIdsResponse)
def add_collection_documents_endpoint(
    collection_id: str,
    payload: CollectionDocumentsRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    document_ids = sorted(set(payload.document_ids))
    for document_id in document_ids:
        document = repository.get(document_id)
        if document is None or document.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document for collection: {document_id}",
            )
    repository.add_collection_documents(
        collection_id=collection_id,
        document_ids=document_ids,
        added_at=datetime.now(UTC),
    )
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.delete("/{collection_id}/documents/{document_id}", response_model=CollectionDocumentIdsResponse)
def remove_collection_document_endpoint(
    collection_id: str,
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    repository.remove_collection_document(collection_id, document_id)
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.post("/search", response_model=SearchResponse)
def search_all_documents_endpoint(
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return SearchResponse.from_chunk_hits(
        repository=repository,
        query=payload.query,
        limit=payload.limit,
        hits=hits,
    )


@router.post("/{collection_id}/search", response_model=SearchResponse)
def search_collection_documents_endpoint(
    collection_id: str,
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=collection_doc_ids,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return SearchResponse.from_chunk_hits(
        repository=repository,
        query=payload.query,
        limit=payload.limit,
        hits=hits,
    )


@router.post("/ask", response_model=AskResponse)
def ask_all_documents_endpoint(
    payload: AskRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    return _ask_grounded(
        repository=repository,
        llm_provider=llm_provider,
        owner_id=current_user.id,
        question=payload.question,
        top_k_chunks=payload.top_k_chunks,
        max_documents=payload.max_documents,
        document_ids=scoped_ids,
        debug_scope={
            "collection_id": None,
            "tag": payload.tag,
            "document_type": payload.document_type,
            "scoped_document_count": len(scoped_ids) if scoped_ids is not None else None,
        },
        debug_enabled=payload.debug,
    )


@router.post("/{collection_id}/ask", response_model=AskResponse)
def ask_collection_documents_endpoint(
    collection_id: str,
    payload: AskRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=collection_doc_ids,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    return _ask_grounded(
        repository=repository,
        llm_provider=llm_provider,
        owner_id=current_user.id,
        question=payload.question,
        top_k_chunks=payload.top_k_chunks,
        max_documents=payload.max_documents,
        document_ids=scoped_ids,
        debug_scope={
            "collection_id": collection_id,
            "tag": payload.tag,
            "document_type": payload.document_type,
            "scoped_document_count": len(scoped_ids) if scoped_ids is not None else None,
        },
        debug_enabled=payload.debug,
    )
