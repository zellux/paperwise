from threading import RLock

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import Document, DocumentHistoryEvent, LLMParseResult, ParseResult


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _to_title_case(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned
    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
            continue
        words.append(word[:1].upper() + word[1:].lower() if word else word)
    return " ".join(words)


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._parse_results: dict[str, ParseResult] = {}
        self._llm_parse_results: dict[str, LLMParseResult] = {}
        self._history: dict[str, list[DocumentHistoryEvent]] = {}
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
            normalized_tags: list[str] = []
            seen_tags: set[str] = set()
            for tag in result.tags:
                normalized = _normalize_name(tag)
                if not normalized or normalized in seen_tags:
                    continue
                seen_tags.add(normalized)
                normalized_tags.append(_to_title_case(tag))

            normalized_created_tags: list[str] = []
            seen_created: set[str] = set()
            for tag in result.created_tags:
                normalized = _normalize_name(tag)
                if not normalized or normalized in seen_created:
                    continue
                seen_created.add(normalized)
                normalized_created_tags.append(_to_title_case(tag))

            result.tags = normalized_tags
            result.created_tags = normalized_created_tags
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
            by_norm: dict[str, str] = {}
            for tag in self._tags:
                normalized = _normalize_name(tag)
                if not normalized:
                    continue
                by_norm[normalized] = _to_title_case(tag)
            return sorted(by_norm.values())

    def list_tag_stats(self) -> list[tuple[str, int]]:
        with self._lock:
            counts: dict[str, int] = {}
            display_name_by_key: dict[str, str] = {}
            for result in self._llm_parse_results.values():
                seen: set[str] = set()
                for tag in result.tags:
                    cleaned = tag.strip()
                    if not cleaned:
                        continue
                    # Count each document at most once per tag.
                    key = cleaned.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    if key not in display_name_by_key:
                        display_name_by_key[key] = _to_title_case(cleaned)
                    counts[key] = counts.get(key, 0) + 1
            return sorted(
                [(display_name_by_key[key], count) for key, count in counts.items()],
                key=lambda item: (-item[1], item[0].casefold()),
            )

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
                    self._tags.add(_to_title_case(cleaned))

    def append_history_events(self, events: list[DocumentHistoryEvent]) -> None:
        if not events:
            return
        with self._lock:
            for event in events:
                self._history.setdefault(event.document_id, []).append(event)

    def list_history(
        self,
        document_id: str,
        *,
        limit: int = 100,
    ) -> list[DocumentHistoryEvent]:
        with self._lock:
            events = sorted(
                self._history.get(document_id, []),
                key=lambda event: event.created_at,
                reverse=True,
            )
            return events[:limit]
