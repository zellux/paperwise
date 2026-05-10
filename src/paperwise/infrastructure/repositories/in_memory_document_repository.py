from datetime import UTC, datetime
from threading import RLock

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.search_text import extract_search_snippet, tokenize_search_query
from paperwise.application.services.taxonomy import normalize_name, to_title_case
from paperwise.application.services.taxonomy_stats import (
    correspondent_stats_from_metadata,
    document_type_stats_from_metadata,
    tag_stats_from_metadata,
)
from paperwise.domain.models import (
    ChatThread,
    Collection,
    DocumentChunk,
    DocumentChunkSearchHit,
    Document,
    DocumentSearchHit,
    DocumentHistoryEvent,
    DocumentStatus,
    LLMParseResult,
    ParseResult,
    UserPreference,
    User,
)


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._users: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._user_preferences: dict[str, UserPreference] = {}
        self._chat_threads: dict[str, ChatThread] = {}
        self._parse_results: dict[str, ParseResult] = {}
        self._llm_parse_results: dict[str, LLMParseResult] = {}
        self._history: dict[str, list[DocumentHistoryEvent]] = {}
        self._collections: dict[str, Collection] = {}
        self._collection_documents: dict[str, dict[str, datetime]] = {}
        self._document_chunks: dict[str, list[DocumentChunk]] = {}
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

    def get_by_owner_checksum(self, owner_id: str, checksum_sha256: str) -> Document | None:
        with self._lock:
            for document in self._documents.values():
                if document.owner_id == owner_id and document.checksum_sha256 == checksum_sha256:
                    return document
            return None

    def list_documents(self, limit: int = 100, *, offset: int = 0) -> list[Document]:
        with self._lock:
            docs = sorted(
                self._documents.values(),
                key=lambda d: d.created_at,
                reverse=True,
            )
            start = max(0, offset)
            end = start + max(0, limit)
            return docs[start:end]

    def list_owner_documents_with_llm_results(
        self,
        *,
        owner_id: str,
        limit: int = 100,
        offset: int = 0,
        statuses: set[DocumentStatus] | None = None,
    ) -> list[tuple[Document, LLMParseResult | None]]:
        if statuses is not None and not statuses:
            return []
        with self._lock:
            docs = sorted(
                (
                    document
                    for document in self._documents.values()
                    if document.owner_id == owner_id
                    and (statuses is None or document.status in statuses)
                ),
                key=lambda d: d.created_at,
                reverse=True,
            )
            start = max(0, offset)
            end = start + max(0, limit)
            return [
                (document, self._llm_parse_results.get(document.id))
                for document in docs[start:end]
            ]

    def count_owner_documents_by_statuses(
        self,
        *,
        owner_id: str,
        statuses: set[DocumentStatus],
    ) -> int:
        with self._lock:
            return sum(
                1
                for document in self._documents.values()
                if document.owner_id == owner_id and document.status in statuses
            )

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            self._documents.pop(document_id, None)
            self._parse_results.pop(document_id, None)
            self._llm_parse_results.pop(document_id, None)
            self._history.pop(document_id, None)
            self._document_chunks.pop(document_id, None)
            now = datetime.now(UTC)
            for collection_id, docs in self._collection_documents.items():
                if docs.pop(document_id, None) is None:
                    continue
                collection = self._collections.get(collection_id)
                if collection is not None:
                    collection.updated_at = now

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
                normalized = normalize_name(tag)
                if not normalized or normalized in seen_tags:
                    continue
                seen_tags.add(normalized)
                normalized_tags.append(to_title_case(tag))

            normalized_created_tags: list[str] = []
            seen_created: set[str] = set()
            for tag in result.created_tags:
                normalized = normalize_name(tag)
                if not normalized or normalized in seen_created:
                    continue
                seen_created.add(normalized)
                normalized_created_tags.append(to_title_case(tag))

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
                normalized = normalize_name(tag)
                if not normalized:
                    continue
                by_norm[normalized] = to_title_case(tag)
            return sorted(by_norm.values())

    def list_tag_stats(self) -> list[tuple[str, int]]:
        with self._lock:
            return tag_stats_from_metadata(self._llm_parse_results.values())

    def list_owner_tag_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._lock:
            results = [
                result
                for document_id, result in self._llm_parse_results.items()
                if self._documents.get(document_id) is not None
                and self._documents[document_id].owner_id == owner_id
            ]
            return tag_stats_from_metadata(results)

    def list_owner_document_type_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._lock:
            results = [
                result
                for document_id, result in self._llm_parse_results.items()
                if self._documents.get(document_id) is not None
                and self._documents[document_id].owner_id == owner_id
            ]
            return document_type_stats_from_metadata(results)

    def list_owner_correspondent_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._lock:
            results = [
                result
                for document_id, result in self._llm_parse_results.items()
                if self._documents.get(document_id) is not None
                and self._documents[document_id].owner_id == owner_id
            ]
            return correspondent_stats_from_metadata(results)

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
                    self._tags.add(to_title_case(cleaned))

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

    def save_user(self, user: User) -> None:
        with self._lock:
            email_key = user.email.strip().lower()
            self._users[user.id] = user
            self._users_by_email[email_key] = user

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        with self._lock:
            return self._users_by_email.get(email.strip().lower())

    def list_users(self, limit: int = 100) -> list[User]:
        with self._lock:
            users = sorted(
                self._users.values(),
                key=lambda user: user.created_at,
                reverse=True,
            )
            return users[:limit]

    def save_user_preference(self, preference: UserPreference) -> None:
        with self._lock:
            self._user_preferences[preference.user_id] = UserPreference(
                user_id=preference.user_id,
                preferences=dict(preference.preferences or {}),
            )

    def get_user_preference(self, user_id: str) -> UserPreference | None:
        with self._lock:
            preference = self._user_preferences.get(user_id)
            if preference is None:
                return None
            return UserPreference(
                user_id=preference.user_id,
                preferences=dict(preference.preferences or {}),
            )

    def save_chat_thread(self, thread: ChatThread) -> None:
        with self._lock:
            self._chat_threads[thread.id] = ChatThread(
                id=thread.id,
                owner_id=thread.owner_id,
                title=thread.title,
                messages=[dict(message) for message in thread.messages],
                token_usage=dict(thread.token_usage or {}),
                created_at=thread.created_at,
                updated_at=thread.updated_at,
            )

    def get_chat_thread(self, owner_id: str, thread_id: str) -> ChatThread | None:
        with self._lock:
            thread = self._chat_threads.get(thread_id)
            if thread is None or thread.owner_id != owner_id:
                return None
            return ChatThread(
                id=thread.id,
                owner_id=thread.owner_id,
                title=thread.title,
                messages=[dict(message) for message in thread.messages],
                token_usage=dict(thread.token_usage or {}),
                created_at=thread.created_at,
                updated_at=thread.updated_at,
            )

    def list_chat_threads(self, owner_id: str, limit: int = 20) -> list[ChatThread]:
        with self._lock:
            threads = [thread for thread in self._chat_threads.values() if thread.owner_id == owner_id]
            threads.sort(key=lambda item: item.updated_at, reverse=True)
            return [
                ChatThread(
                    id=thread.id,
                    owner_id=thread.owner_id,
                    title=thread.title,
                    messages=[dict(message) for message in thread.messages],
                    token_usage=dict(thread.token_usage or {}),
                    created_at=thread.created_at,
                    updated_at=thread.updated_at,
                )
                for thread in threads[: max(0, limit)]
            ]

    def delete_chat_thread(self, owner_id: str, thread_id: str) -> bool:
        with self._lock:
            thread = self._chat_threads.get(thread_id)
            if thread is None or thread.owner_id != owner_id:
                return False
            del self._chat_threads[thread_id]
            return True

    def create_collection(self, collection: Collection) -> None:
        with self._lock:
            self._collections[collection.id] = collection

    def get_collection(self, collection_id: str) -> Collection | None:
        with self._lock:
            return self._collections.get(collection_id)

    def list_collections(self, owner_id: str) -> list[Collection]:
        with self._lock:
            items = [c for c in self._collections.values() if c.owner_id == owner_id]
            return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def delete_collection(self, collection_id: str) -> None:
        with self._lock:
            self._collections.pop(collection_id, None)
            self._collection_documents.pop(collection_id, None)

    def add_collection_documents(
        self,
        collection_id: str,
        document_ids: list[str],
        *,
        added_at: datetime,
    ) -> None:
        with self._lock:
            docs = self._collection_documents.setdefault(collection_id, {})
            for document_id in document_ids:
                docs[document_id] = added_at
            collection = self._collections.get(collection_id)
            if collection is not None:
                collection.updated_at = datetime.now(UTC)

    def remove_collection_document(self, collection_id: str, document_id: str) -> None:
        with self._lock:
            docs = self._collection_documents.get(collection_id)
            if docs is not None:
                docs.pop(document_id, None)
            collection = self._collections.get(collection_id)
            if collection is not None:
                collection.updated_at = datetime.now(UTC)

    def list_collection_document_ids(self, collection_id: str) -> list[str]:
        with self._lock:
            docs = self._collection_documents.get(collection_id, {})
            return sorted(docs.keys())

    def search_documents(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[DocumentSearchHit]:
        terms = tokenize_search_query(query)
        if not terms:
            return []
        allowed_ids = set(document_ids or [])
        has_scope = bool(document_ids is not None)
        hits: list[DocumentSearchHit] = []
        with self._lock:
            docs = [
                doc
                for doc in self._documents.values()
                if doc.owner_id == owner_id and (not has_scope or doc.id in allowed_ids)
            ]
            docs.sort(key=lambda item: item.created_at, reverse=True)
            for doc in docs:
                parse_result = self._parse_results.get(doc.id)
                llm = self._llm_parse_results.get(doc.id)
                searchable_parts = [
                    doc.filename,
                    parse_result.text_preview if parse_result is not None else "",
                    llm.suggested_title if llm is not None else "",
                    llm.correspondent if llm is not None else "",
                    llm.document_type if llm is not None else "",
                    " ".join(llm.tags) if llm is not None else "",
                ]
                searchable_text = " ".join(part for part in searchable_parts if part).strip()
                lowered = searchable_text.lower()
                matched = [term for term in terms if term in lowered]
                if not matched:
                    continue
                score = float(sum(lowered.count(term) for term in matched))
                snippet = extract_search_snippet(
                    parse_result.text_preview if parse_result is not None else searchable_text,
                    matched,
                )
                hits.append(
                    DocumentSearchHit(
                        document=doc,
                        score=score,
                        snippet=snippet,
                        matched_terms=matched,
                    )
                )
        hits.sort(key=lambda hit: (hit.score, hit.document.created_at), reverse=True)
        return hits[: max(1, limit)]

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        owner_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        del owner_id
        with self._lock:
            self._document_chunks[document_id] = list(chunks)

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        with self._lock:
            return list(self._document_chunks.get(document_id, []))

    def search_document_chunks(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 40,
        document_ids: list[str] | None = None,
    ) -> list[DocumentChunkSearchHit]:
        terms = tokenize_search_query(query)
        if not terms:
            return []
        allowed_ids = set(document_ids or [])
        has_scope = document_ids is not None
        hits: list[DocumentChunkSearchHit] = []
        with self._lock:
            for doc_id, chunks in self._document_chunks.items():
                if has_scope and doc_id not in allowed_ids:
                    continue
                document = self._documents.get(doc_id)
                if document is None or document.owner_id != owner_id:
                    continue
                for chunk in chunks:
                    lowered = chunk.content.lower()
                    matched = [term for term in terms if term in lowered]
                    if not matched:
                        continue
                    score = float(sum(lowered.count(term) for term in matched))
                    hits.append(
                        DocumentChunkSearchHit(
                            chunk=chunk,
                            score=score,
                            matched_terms=matched,
                        )
                    )
        hits.sort(key=lambda item: (item.score, item.chunk.created_at, item.chunk.chunk_index), reverse=True)
        return hits[: max(1, limit)]
