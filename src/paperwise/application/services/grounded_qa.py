from datetime import datetime
import re
from typing import Any

import httpx

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.document_listing import normalized_values
from paperwise.application.services.taxonomy import normalize_name
from paperwise.domain.models import DocumentChunkSearchHit, User


def is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    return "timed out" in str(exc).lower()


def resolve_metadata_scoped_document_ids(
    *,
    repository: DocumentRepository,
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
        if len(documents) < batch_size:
            break
        offset += batch_size
    return sorted(matched_ids)


def search_document_chunks_multi_query(
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


def build_qa_contexts(
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
