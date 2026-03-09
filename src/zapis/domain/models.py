from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass(slots=True)
class Document:
    id: str
    filename: str
    owner_id: str
    status: DocumentStatus
    created_at: datetime

