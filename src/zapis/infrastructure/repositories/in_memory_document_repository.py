from threading import RLock

from zapis.application.interfaces import DocumentRepository
from zapis.domain.models import Document, LLMParseResult, ParseResult


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._parse_results: dict[str, ParseResult] = {}
        self._llm_parse_results: dict[str, LLMParseResult] = {}
        self._correspondents: set[str] = set()
        self._document_types: set[str] = set()
        self._tags: set[str] = set()
        self._lock = RLock()

    def save(self, document: Document) -> None:
        with self._lock:
            self._documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

    def list_documents(self, limit: int = 100) -> list[Document]:
        with self._lock:
            docs = sorted(
                self._documents.values(),
                key=lambda d: d.created_at,
                reverse=True,
            )
            return docs[:limit]

    def save_parse_result(self, result: ParseResult) -> None:
        with self._lock:
            self._parse_results[result.document_id] = result

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        with self._lock:
            return self._parse_results.get(document_id)

    def save_llm_parse_result(self, result: LLMParseResult) -> None:
        with self._lock:
            self._llm_parse_results[result.document_id] = result

    def get_llm_parse_result(self, document_id: str) -> LLMParseResult | None:
        with self._lock:
            return self._llm_parse_results.get(document_id)

    def list_correspondents(self) -> list[str]:
        with self._lock:
            return sorted(self._correspondents)

    def list_document_types(self) -> list[str]:
        with self._lock:
            return sorted(self._document_types)

    def list_tags(self) -> list[str]:
        with self._lock:
            return sorted(self._tags)

    def add_correspondent(self, name: str) -> None:
        with self._lock:
            self._correspondents.add(name.strip())

    def add_document_type(self, name: str) -> None:
        with self._lock:
            self._document_types.add(name.strip())

    def add_tags(self, names: list[str]) -> None:
        with self._lock:
            for name in names:
                cleaned = name.strip()
                if cleaned:
                    self._tags.add(cleaned)
