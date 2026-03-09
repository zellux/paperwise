from threading import RLock

from zapis.application.interfaces import DocumentRepository
from zapis.domain.models import Document, ParseResult


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._parse_results: dict[str, ParseResult] = {}
        self._lock = RLock()

    def save(self, document: Document) -> None:
        with self._lock:
            self._documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

    def save_parse_result(self, result: ParseResult) -> None:
        with self._lock:
            self._parse_results[result.document_id] = result

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        with self._lock:
            return self._parse_results.get(document_id)
