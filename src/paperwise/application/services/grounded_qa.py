from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Callable, Protocol

import httpx

from paperwise.application.interfaces import DocumentChunkRepository, DocumentStore, LLMProvider, ParseResultRepository
from paperwise.application.services.document_listing import normalized_values
from paperwise.application.services.taxonomy import normalize_name
from paperwise.domain.models import DocumentChunkSearchHit, User


class MetadataScopeRepository(DocumentStore, Protocol):
    pass


class QAContextRepository(DocumentStore, ParseResultRepository, Protocol):
    pass


class GroundedQARepository(DocumentChunkRepository, QAContextRepository, Protocol):
    pass


class GroundedQATimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class GroundedQACitation:
    chunk_id: str
    document_id: str
    title: str
    quote: str


@dataclass
class GroundedQAResult:
    question: str
    answer: str
    insufficient_evidence: bool
    citations: list[GroundedQACitation]
    debug: dict[str, Any] | None = None


LogExchange = Callable[
    [str, str, dict[str, Any], int | None, Any, str | None],
    None,
]


def is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    return "timed out" in str(exc).lower()


def resolve_metadata_scoped_document_ids(
    *,
    repository: MetadataScopeRepository,
    current_user: User,
    base_document_ids: list[str] | None,
    tag_filters: list[str] | None,
    document_type_filters: list[str] | None,
    correspondent_filters: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    title_query: str | None = None,
) -> list[str] | None:
    normalized_tags = normalized_values(tag_filters)
    normalized_document_types = normalized_values(document_type_filters)
    normalized_correspondents = normalized_values(correspondent_filters)
    title_terms = normalized_values([title_query] if title_query else [])
    parsed_date_from = _parse_iso_date_filter(date_from)
    parsed_date_to = _parse_iso_date_filter(date_to)
    if (
        not normalized_tags
        and not normalized_document_types
        and not normalized_correspondents
        and not parsed_date_from
        and not parsed_date_to
        and not title_terms
    ):
        if base_document_ids is None:
            return None
        return sorted(set(base_document_ids))

    scoped_ids = set(base_document_ids) if base_document_ids is not None else None
    matched_ids: list[str] = []
    seen_ids: set[str] = set()
    batch_size = 1000
    offset = 0
    while True:
        documents_with_metadata = repository.list_owner_documents_with_llm_results(
            owner_id=current_user.id,
            limit=batch_size,
            offset=offset,
        )
        if not documents_with_metadata:
            break
        for document, llm_result in documents_with_metadata:
            if scoped_ids is not None and document.id not in scoped_ids:
                continue
            if llm_result is None:
                continue
            if normalized_tags:
                doc_tags = {normalize_name(tag) for tag in llm_result.tags}
                if not normalized_tags.intersection(doc_tags):
                    continue
            if normalized_document_types:
                if normalize_name(llm_result.document_type) not in normalized_document_types:
                    continue
            if normalized_correspondents:
                if normalize_name(llm_result.correspondent) not in normalized_correspondents:
                    continue
            document_date = _parse_iso_date_filter(llm_result.document_date)
            if parsed_date_from and (document_date is None or document_date < parsed_date_from):
                continue
            if parsed_date_to and (document_date is None or document_date > parsed_date_to):
                continue
            if title_terms:
                title = llm_result.suggested_title or document.filename
                normalized_title = normalize_name(title)
                if not all(term in normalized_title for term in title_terms):
                    continue
            if document.id in seen_ids:
                continue
            seen_ids.add(document.id)
            matched_ids.append(document.id)
        if len(documents_with_metadata) < batch_size:
            break
        offset += batch_size
    return sorted(matched_ids)


def search_document_chunks_multi_query(
    *,
    repository: DocumentChunkRepository,
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


def build_qa_contexts(
    *,
    repository: QAContextRepository,
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


def answer_grounded_question(
    *,
    repository: GroundedQARepository,
    llm_provider: LLMProvider,
    owner_id: str,
    question: str,
    top_k_chunks: int,
    max_documents: int,
    document_ids: list[str] | None,
    debug_scope: dict[str, object] | None = None,
    debug_enabled: bool = False,
    log_exchange: LogExchange | None = None,
) -> GroundedQAResult:
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
    if not contexts:
        response_debug = {
            "answer": "Not enough evidence in the selected documents.",
            "insufficient_evidence": True,
            "citations": [],
        }
        _log_grounded_qa_exchange(
            log_exchange=log_exchange,
            request_debug=request_debug,
            response_status=200,
            response_payload=response_debug,
        )
        return GroundedQAResult(
            question=question,
            answer="Not enough evidence in the selected documents.",
            insufficient_evidence=True,
            citations=[],
            debug=_debug_payload(request_debug, response_debug) if debug_enabled else None,
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
            _log_grounded_qa_exchange(
                log_exchange=log_exchange,
                request_debug=request_debug,
                response_status=504,
                response_payload={"detail": message},
                error=str(exc),
            )
            raise GroundedQATimeoutError(message) from exc
        raise

    citations: list[GroundedQACitation] = []
    by_chunk = {ctx["chunk_id"]: ctx for ctx in contexts}
    for citation in llm_payload.get("citations", []) if isinstance(llm_payload, dict) else []:
        chunk_id = str(citation.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id not in by_chunk:
            continue
        context = by_chunk[chunk_id]
        citations.append(
            GroundedQACitation(
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

    response_debug = {
        "answer": answer,
        "insufficient_evidence": insufficient,
        "citation_count": len(citations),
        "citations": [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "title": item.title,
                "quote_len": len(item.quote),
            }
            for item in citations
        ],
    }
    _log_grounded_qa_exchange(
        log_exchange=log_exchange,
        request_debug=request_debug,
        response_status=200,
        response_payload=response_debug,
    )
    return GroundedQAResult(
        question=question,
        answer=answer,
        insufficient_evidence=insufficient,
        citations=citations,
        debug=_debug_payload(request_debug, response_debug) if debug_enabled else None,
    )


def _debug_payload(request_debug: dict[str, Any], response_debug: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": request_debug.get("scope"),
        "retrieval": request_debug.get("retrieval"),
        "sources_sent_to_llm": request_debug.get("selected_contexts"),
        "result": response_debug,
    }


def _log_grounded_qa_exchange(
    *,
    log_exchange: LogExchange | None,
    request_debug: dict[str, Any],
    response_status: int | None,
    response_payload: Any,
    error: str | None = None,
) -> None:
    if log_exchange is None:
        return
    log_exchange(
        "grounded_qa",
        "/collections/ask",
        request_debug,
        response_status,
        response_payload,
        error,
    )


def _parse_iso_date_filter(value: str | None):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


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
    queries = _clean_retrieval_terms(queries_raw)
    must_terms = _clean_retrieval_terms(must_terms_raw)
    optional_terms = _clean_retrieval_terms(optional_terms_raw)
    anchor_terms = _clean_retrieval_terms(anchor_terms_raw)
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


def _clean_retrieval_terms(raw_terms: object) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for item in raw_terms if isinstance(raw_terms, list) else []:
        value = " ".join(str(item or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(value)
    return terms


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
