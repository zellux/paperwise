from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class DocumentIngested:
    document_id: str
    occurred_at: datetime


@dataclass(slots=True)
class DocumentParsed:
    document_id: str
    occurred_at: datetime

