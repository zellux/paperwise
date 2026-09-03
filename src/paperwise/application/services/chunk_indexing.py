from __future__ import annotations

from datetime import UTC, datetime
import re

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import (
    Document,
    DocumentChunk,
    DocumentIndexState,
    DocumentIndexStatus,
    ParseResult,
)

DOCUMENT_INDEX_VERSION = "fts-v1"


def _token_count(value: str) -> int:
    return len(re.findall(r"\S+", str(value or "")))


def chunk_text(text: str, *, chunk_size_tokens: int = 220, overlap_tokens: int = 40) -> list[str]:
    tokens = re.findall(r"\S+", str(text or ""))
    if not tokens:
        return []
    size = max(20, chunk_size_tokens)
    overlap = max(0, min(overlap_tokens, size // 2))
    step = max(1, size - overlap)

    chunks: list[str] = []
    i = 0
    while i < len(tokens):
        window = tokens[i : i + size]
        if not window:
            break
        chunks.append(" ".join(window).strip())
        i += step
    return [chunk for chunk in chunks if chunk]


def build_document_chunks(*, document: Document, parse_result: ParseResult) -> list[DocumentChunk]:
    now = datetime.now(UTC)
    raw_chunks = chunk_text(parse_result.full_text or parse_result.text_preview)
    chunks: list[DocumentChunk] = []
    for idx, content in enumerate(raw_chunks):
        chunks.append(
            DocumentChunk(
                id=f"{document.id}:{idx}",
                document_id=document.id,
                owner_id=document.owner_id,
                chunk_index=idx,
                content=content,
                token_count=_token_count(content),
                created_at=now,
            )
        )
    return chunks


def index_document_chunks(
    *,
    repository: DocumentRepository,
    document: Document,
    parse_result: ParseResult,
) -> int:
    started_at = datetime.now(UTC)
    repository.save_document_index_state(
        DocumentIndexState(
            document_id=document.id,
            owner_id=document.owner_id,
            status=DocumentIndexStatus.INDEXING,
            index_version=DOCUMENT_INDEX_VERSION,
            source_checksum=document.checksum_sha256,
            chunk_count=0,
            updated_at=started_at,
        )
    )
    chunks = build_document_chunks(document=document, parse_result=parse_result)
    try:
        repository.replace_document_chunks(
            document_id=document.id,
            owner_id=document.owner_id,
            chunks=chunks,
        )
    except Exception as exc:
        repository.save_document_index_state(
            DocumentIndexState(
                document_id=document.id,
                owner_id=document.owner_id,
                status=DocumentIndexStatus.FAILED,
                index_version=DOCUMENT_INDEX_VERSION,
                source_checksum=document.checksum_sha256,
                chunk_count=0,
                updated_at=datetime.now(UTC),
                last_error=(str(exc).strip() or type(exc).__name__)[:4000],
            )
        )
        raise
    completed_at = datetime.now(UTC)
    repository.save_document_index_state(
        DocumentIndexState(
            document_id=document.id,
            owner_id=document.owner_id,
            status=DocumentIndexStatus.READY,
            index_version=DOCUMENT_INDEX_VERSION,
            source_checksum=document.checksum_sha256,
            chunk_count=len(chunks),
            updated_at=completed_at,
            indexed_at=completed_at,
        )
    )
    return len(chunks)


def mark_document_index_pending(*, repository: DocumentRepository, document: Document) -> None:
    previous = repository.get_document_index_state(document.id)
    repository.save_document_index_state(
        DocumentIndexState(
            document_id=document.id,
            owner_id=document.owner_id,
            status=DocumentIndexStatus.PENDING,
            index_version=DOCUMENT_INDEX_VERSION,
            source_checksum=document.checksum_sha256,
            chunk_count=previous.chunk_count if previous is not None else 0,
            updated_at=datetime.now(UTC),
            indexed_at=previous.indexed_at if previous is not None else None,
        )
    )


def mark_document_index_failed(
    *,
    repository: DocumentRepository,
    document: Document,
    error: str,
) -> None:
    previous = repository.get_document_index_state(document.id)
    repository.save_document_index_state(
        DocumentIndexState(
            document_id=document.id,
            owner_id=document.owner_id,
            status=DocumentIndexStatus.FAILED,
            index_version=DOCUMENT_INDEX_VERSION,
            source_checksum=document.checksum_sha256,
            chunk_count=previous.chunk_count if previous is not None else 0,
            updated_at=datetime.now(UTC),
            indexed_at=previous.indexed_at if previous is not None else None,
            last_error=(str(error).strip() or "Indexing failed")[:4000],
        )
    )


def reindex_document_chunks(*, repository: DocumentRepository, document: Document) -> int:
    parse_result = repository.get_parse_result(document.id)
    if parse_result is None:
        message = "Parse result not found; process the document before indexing."
        repository.save_document_index_state(
            DocumentIndexState(
                document_id=document.id,
                owner_id=document.owner_id,
                status=DocumentIndexStatus.FAILED,
                index_version=DOCUMENT_INDEX_VERSION,
                source_checksum=document.checksum_sha256,
                chunk_count=0,
                updated_at=datetime.now(UTC),
                last_error=message,
            )
        )
        raise RuntimeError(message)
    return index_document_chunks(repository=repository, document=document, parse_result=parse_result)
