from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    READY = "ready"


@dataclass(slots=True)
class Document:
    id: str
    filename: str
    owner_id: str
    blob_uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime


@dataclass(slots=True)
class ParseResult:
    document_id: str
    parser: str
    status: str
    size_bytes: int
    page_count: int
    text_preview: str
    created_at: datetime


@dataclass(slots=True)
class LLMParseResult:
    document_id: str
    suggested_title: str
    document_date: str | None
    correspondent: str
    document_type: str
    tags: list[str]
    created_correspondent: bool
    created_document_type: bool
    created_tags: list[str]
    created_at: datetime
