from threading import RLock

from zapis.application.interfaces import DocumentRepository
from zapis.domain.models import Document


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._lock = RLock()

    def save(self, document: Document) -> None:
        with self._lock:
            self._documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

