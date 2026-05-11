from dataclasses import dataclass
from typing import Any, Callable, Protocol

import httpx

from paperwise.application.interfaces import DocumentChunkRepository, DocumentStore, LLMProvider, ParseResultRepository
from paperwise.application.services.grounded_qa_retrieval import (
    MetadataScopeRepository,
    resolve_metadata_scoped_document_ids,
    search_document_chunks_multi_query,
)

__all__ = [
    "GroundedQACitation",
    "GroundedQARepository",
    "GroundedQAResult",
    "GroundedQATimeoutError",
    "MetadataScopeRepository",
    "answer_grounded_question",
    "build_qa_contexts",
    "is_timeout_error",
    "resolve_metadata_scoped_document_ids",
    "search_document_chunks_multi_query",
]


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
