from __future__ import annotations

from datetime import UTC, datetime
import re

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import Document, DocumentChunk, ParseResult


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
    raw_chunks = chunk_text(parse_result.text_preview)
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
    chunks = build_document_chunks(document=document, parse_result=parse_result)
    repository.replace_document_chunks(
        document_id=document.id,
        owner_id=document.owner_id,
        chunks=chunks,
    )
    return len(chunks)
