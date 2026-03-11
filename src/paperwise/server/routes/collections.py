import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.llm_preferences import LLM_TASK_GROUNDED_QA
from paperwise.domain.models import Collection, DocumentChunkSearchHit, User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.routes.documents import _resolve_llm_provider_from_preferences
from paperwise.infrastructure.llm.debug_log import log_llm_exchange

router = APIRouter(prefix="/collections", tags=["collections"])


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    return "timed out" in str(exc).lower()

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


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[SearchHitResponse]


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


def _to_collection_response(
    *,
    repository: DocumentRepository,
    collection: Collection,
) -> CollectionResponse:
    document_count = len(repository.list_collection_document_ids(collection.id))
    return CollectionResponse(
        id=collection.id,
        owner_id=collection.owner_id,
        name=collection.name,
        description=collection.description,
        document_count=document_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _get_collection_or_404(
    *,
    collection_id: str,
    repository: DocumentRepository,
    current_user: User,
) -> Collection:
    collection = repository.get_collection(collection_id)
    if collection is None or collection.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


def _build_search_response(
    *,
    repository: DocumentRepository,
    query: str,
    limit: int,
    hits,
) -> SearchResponse:
    best_hits_by_doc: dict[str, tuple[object, float]] = {}
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
        hit = best_hits_by_doc[doc_id][0]
        document = repository.get(doc_id)
        if document is None:
            continue
        llm = repository.get_llm_parse_result(doc_id)
        title = llm.suggested_title if llm is not None and llm.suggested_title else document.filename
        items.append(
            SearchHitResponse(
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
        )
        if len(items) >= max(1, limit):
            break
    return SearchResponse(query=query, total_hits=len(items), hits=items)


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _normalized_values(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for part in value.split(","):
            item = _normalize_name(part)
            if item:
                normalized.add(item)
    return normalized


def _resolve_metadata_scoped_document_ids(
    *,
    repository: DocumentRepository,
    current_user: User,
    base_document_ids: list[str] | None,
    tag_filters: list[str] | None,
    document_type_filters: list[str] | None,
) -> list[str] | None:
    normalized_tags = _normalized_values(tag_filters)
    normalized_document_types = _normalized_values(document_type_filters)
    if not normalized_tags and not normalized_document_types:
        if base_document_ids is None:
            return None
        return sorted(set(base_document_ids))

    scoped_ids = set(base_document_ids) if base_document_ids is not None else None
    matched_ids: list[str] = []
    seen_ids: set[str] = set()
    batch_size = 1000
    offset = 0
    while True:
        documents = repository.list_documents(limit=batch_size, offset=offset)
        if not documents:
            break
        for document in documents:
            if document.owner_id != current_user.id:
                continue
            if scoped_ids is not None and document.id not in scoped_ids:
                continue
            llm_result = repository.get_llm_parse_result(document.id)
            if llm_result is None:
                continue
            if normalized_tags:
                doc_tags = {_normalize_name(tag) for tag in llm_result.tags}
                if not normalized_tags.intersection(doc_tags):
                    continue
            if normalized_document_types:
                if _normalize_name(llm_result.document_type) not in normalized_document_types:
                    continue
            if document.id in seen_ids:
                continue
            seen_ids.add(document.id)
            matched_ids.append(document.id)
        if len(documents) < batch_size:
            break
        offset += batch_size
    return sorted(matched_ids)


def _build_retrieval_queries_heuristic(query: str) -> list[str]:
    compact = " ".join(str(query or "").split()).strip()
    if not compact:
        return []
    lowered = compact.lower()
    tokens = re.findall(r"[a-z0-9]+", lowered)
    token_set = set(tokens)
    variants: list[str] = [compact]

    def add(value: str) -> None:
        candidate = " ".join(str(value or "").split()).strip()
        if not candidate:
            return
        if candidate.lower() in {item.lower() for item in variants}:
            return
        variants.append(candidate)

    if {"measurement", "measurements", "list"}.intersection(token_set):
        add(f"{compact} values")
        add(f"{compact} vital signs")
    if "weight" in token_set:
        add(compact.replace("weight", "body weight"))
        add(f"{compact} lb lbs kg")
    if "mass" in token_set:
        add(compact.replace("mass", "weight"))
        add(f"{compact} body weight")
    if "vitals" in token_set or ("vital" in token_set and "signs" in token_set):
        add(f"{compact} weight height blood pressure pulse")
    return variants[:6]


def _build_retrieval_queries_with_llm(
    *,
    query: str,
    llm_provider: LLMProvider | None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fallback = _build_retrieval_queries_heuristic(query)
    if llm_provider is None:
        if debug is not None:
            debug["rewrite_source"] = "heuristic"
            debug["rewrite_reason"] = "no_llm_provider"
        return {"queries": fallback, "must_terms": [], "anchor_terms": [], "optional_terms": []}
    rewrite_method = getattr(llm_provider, "rewrite_retrieval_queries", None)
    if not callable(rewrite_method):
        if debug is not None:
            debug["rewrite_source"] = "heuristic"
            debug["rewrite_reason"] = "provider_without_rewrite_method"
        return {"queries": fallback, "must_terms": [], "anchor_terms": [], "optional_terms": []}
    try:
        rewritten = rewrite_method(question=query)
    except Exception as exc:
        if debug is not None:
            debug["rewrite_source"] = "heuristic"
            debug["rewrite_reason"] = f"llm_rewrite_error:{exc}"
        return {"queries": fallback, "must_terms": [], "anchor_terms": [], "optional_terms": []}

    queries_raw = rewritten.get("queries", []) if isinstance(rewritten, dict) else []
    must_terms_raw = rewritten.get("must_terms", []) if isinstance(rewritten, dict) else []
    anchor_terms_raw = rewritten.get("anchor_terms", []) if isinstance(rewritten, dict) else []
    optional_terms_raw = rewritten.get("optional_terms", []) if isinstance(rewritten, dict) else []
    queries: list[str] = []
    seen: set[str] = set()
    for item in queries_raw if isinstance(queries_raw, list) else []:
        value = " ".join(str(item or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(value)
    must_terms: list[str] = []
    seen.clear()
    for item in must_terms_raw if isinstance(must_terms_raw, list) else []:
        value = " ".join(str(item or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        must_terms.append(value)
    optional_terms: list[str] = []
    seen.clear()
    for item in optional_terms_raw if isinstance(optional_terms_raw, list) else []:
        value = " ".join(str(item or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        optional_terms.append(value)
    anchor_terms: list[str] = []
    seen.clear()
    for item in anchor_terms_raw if isinstance(anchor_terms_raw, list) else []:
        value = " ".join(str(item or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        anchor_terms.append(value)
    if not queries:
        if debug is not None:
            debug["rewrite_source"] = "heuristic"
            debug["rewrite_reason"] = "llm_rewrite_empty"
        return {
            "queries": fallback,
            "must_terms": must_terms[:12],
            "anchor_terms": anchor_terms[:12],
            "optional_terms": optional_terms[:18],
        }
    if debug is not None:
        debug["rewrite_source"] = "llm"
        debug["llm_rewrite"] = rewritten if isinstance(rewritten, dict) else {"raw": rewritten}
    return {
        "queries": queries[:6],
        "must_terms": must_terms[:12],
        "anchor_terms": anchor_terms[:12],
        "optional_terms": optional_terms[:18],
    }


def _term_coverage_count(text: str, terms: list[str]) -> int:
    lowered = str(text or "").lower()
    return sum(1 for term in terms if " ".join(str(term or "").lower().split()).strip() in lowered)


def _extract_strong_terms(terms: list[str]) -> list[str]:
    strong_terms: list[str] = []
    seen: set[str] = set()

    def add_candidate(candidate: str) -> None:
        simple = re.sub(r"[^a-z0-9]+", " ", candidate).strip()
        if not simple:
            return
        if len(simple) < 3 and simple not in {"lb", "kg", "cm", "in"}:
            return
        if simple in seen:
            return
        seen.add(simple)
        strong_terms.append(simple)

    for term in terms:
        normalized = " ".join(str(term or "").lower().split()).strip()
        if not normalized:
            continue
        add_candidate(normalized)
        if " " in normalized:
            for token in normalized.split():
                add_candidate(token)
    return strong_terms


def _search_document_chunks_multi_query(
    *,
    repository: DocumentRepository,
    owner_id: str,
    query: str,
    limit: int,
    document_ids: list[str] | None,
    llm_provider: LLMProvider | None = None,
    debug: dict | None = None,
) -> list[DocumentChunkSearchHit]:
    rewrite_payload = _build_retrieval_queries_with_llm(
        query=query,
        llm_provider=llm_provider,
        debug=debug,
    )
    retrieval_queries = list(rewrite_payload.get("queries", []))
    must_terms = [str(item) for item in rewrite_payload.get("must_terms", [])]
    anchor_terms = [str(item) for item in rewrite_payload.get("anchor_terms", [])]
    optional_terms = [str(item) for item in rewrite_payload.get("optional_terms", [])]
    strong_must_terms = _extract_strong_terms(anchor_terms if anchor_terms else must_terms)
    if debug is not None:
        debug["expanded_queries"] = list(retrieval_queries)
        debug["must_terms"] = must_terms
        debug["anchor_terms"] = anchor_terms
        debug["optional_terms"] = optional_terms
        debug["strong_must_terms"] = strong_must_terms
        debug["per_query"] = []
    if not retrieval_queries:
        return []
    best_by_chunk: dict[str, DocumentChunkSearchHit] = {}
    for candidate in retrieval_queries:
        hits = repository.search_document_chunks(
            owner_id=owner_id,
            query=candidate,
            limit=limit,
            document_ids=document_ids,
        )
        if debug is not None:
            debug["per_query"].append(
                {
                    "query": candidate,
                    "hit_count": len(hits),
                    "top_chunk_ids": [hit.chunk.id for hit in hits[:5]],
                }
            )
        for hit in hits:
            chunk_id = hit.chunk.id
            existing = best_by_chunk.get(chunk_id)
            if existing is None:
                best_by_chunk[chunk_id] = hit
                continue
            merged_terms = sorted(set(existing.matched_terms).union(hit.matched_terms))
            if float(hit.score) > float(existing.score):
                best_by_chunk[chunk_id] = DocumentChunkSearchHit(
                    chunk=hit.chunk,
                    score=hit.score,
                    matched_terms=merged_terms,
                )
                continue
            best_by_chunk[chunk_id] = DocumentChunkSearchHit(
                chunk=existing.chunk,
                score=existing.score,
                matched_terms=merged_terms,
            )
    merged = sorted(best_by_chunk.values(), key=lambda item: float(item.score), reverse=True)
    if strong_must_terms:
        required_count = 2 if len(strong_must_terms) >= 2 else 1
        anchor_filtered = [
            item
            for item in merged
            if _term_coverage_count(item.chunk.content, strong_must_terms) >= required_count
        ]
        if anchor_filtered:
            merged = anchor_filtered
            if debug is not None:
                debug["anchor_filter_applied"] = True
                debug["anchor_filter_required_count"] = required_count
        elif debug is not None:
            debug["anchor_filter_applied"] = False
            debug["anchor_filter_required_count"] = required_count
            debug["anchor_filter_fallback"] = "no_chunks_met_anchor_threshold"
    merged = sorted(
        merged,
        key=lambda item: (
            _term_coverage_count(item.chunk.content, strong_must_terms),
            _term_coverage_count(item.chunk.content, optional_terms),
            float(item.score),
        ),
        reverse=True,
    )[:limit]
    if debug is not None:
        debug["merged_hit_count"] = len(merged)
        debug["merged_top_chunk_ids"] = [item.chunk.id for item in merged[:10]]
        debug["merged_term_coverage"] = [
            {
                "chunk_id": item.chunk.id,
                "strong_must_term_matches": _term_coverage_count(item.chunk.content, strong_must_terms),
                "optional_term_matches": _term_coverage_count(item.chunk.content, optional_terms),
            }
            for item in merged[:10]
        ]
    return merged


def _build_qa_contexts(
    *,
    repository: DocumentRepository,
    chunk_hits,
    top_k_chunks: int,
    max_documents: int,
) -> list[dict[str, str]]:
    contexts: list[dict[str, str]] = []
    seen_chunk_ids: set[str] = set()
    selected_document_ids: set[str] = set()
    for hit in chunk_hits:
        chunk = hit.chunk
        if chunk.id in seen_chunk_ids:
            continue
        if chunk.document_id not in selected_document_ids and len(selected_document_ids) >= max_documents:
            continue
        seen_chunk_ids.add(chunk.id)
        llm = repository.get_llm_parse_result(chunk.document_id)
        document = repository.get(chunk.document_id)
        if document is None:
            continue
        selected_document_ids.add(chunk.document_id)
        title = llm.suggested_title if llm is not None and llm.suggested_title else document.filename
        contexts.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": title,
                "content": chunk.content,
            }
        )
        if len(contexts) >= top_k_chunks:
            break
    return contexts


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
    chunk_hits = _search_document_chunks_multi_query(
        repository=repository,
        owner_id=owner_id,
        query=question,
        limit=max(top_k_chunks * 3, top_k_chunks),
        document_ids=document_ids,
        llm_provider=llm_provider,
        debug=retrieval_debug,
    )
    contexts = _build_qa_contexts(
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
        if _is_timeout_error(exc):
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
    return _to_collection_response(repository=repository, collection=collection)


@router.get("", response_model=list[CollectionResponse])
def list_collections_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[CollectionResponse]:
    collections = repository.list_collections(current_user.id)
    return [_to_collection_response(repository=repository, collection=item) for item in collections]


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    collection = _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return _to_collection_response(repository=repository, collection=collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    _get_collection_or_404(
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
    _get_collection_or_404(
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
    _get_collection_or_404(
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
    _get_collection_or_404(
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
    scoped_ids = _resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = _search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return _build_search_response(repository=repository, query=payload.query, limit=payload.limit, hits=hits)


@router.post("/{collection_id}/search", response_model=SearchResponse)
def search_collection_documents_endpoint(
    collection_id: str,
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = _resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=collection_doc_ids,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = _search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return _build_search_response(repository=repository, query=payload.query, limit=payload.limit, hits=hits)


@router.post("/ask", response_model=AskResponse)
def ask_all_documents_endpoint(
    payload: AskRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    llm_provider = _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    scoped_ids = _resolve_metadata_scoped_document_ids(
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
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    llm_provider = _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = _resolve_metadata_scoped_document_ids(
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
