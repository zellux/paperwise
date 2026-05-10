from collections.abc import Callable
from datetime import UTC, datetime
import re

from sqlalchemy import func, select

from paperwise.application.interfaces import DocumentRepository
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
    HistoryActorType,
    HistoryEventType,
    LLMParseResult,
    ParseResult,
    UserPreference,
    User,
)
from paperwise.infrastructure.db import Base, build_engine, build_session_factory
from paperwise.infrastructure.repositories.postgres_models import (
    ChatThreadRow,
    CollectionDocumentRow,
    CollectionRow,
    CorrespondentRow,
    DocumentRow,
    DocumentChunkRow,
    DocumentHistoryEventRow,
    DocumentTypeRow,
    LLMParseResultRow,
    ParseResultRow,
    TagRow,
    UserPreferenceRow,
    UserRow,
)


def _coerce_document_status(value: str) -> DocumentStatus:
    legacy_map = {
        "parsing": DocumentStatus.PROCESSING,
        "parsed": DocumentStatus.PROCESSING,
        "enriching": DocumentStatus.PROCESSING,
        "failed": DocumentStatus.PROCESSING,
    }
    normalized = (value or "").strip().lower()
    if normalized in legacy_map:
        return legacy_map[normalized]
    return DocumentStatus(normalized)


def _tokenize_query(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]{2,}", query)]


def _extract_snippet(text: str, terms: list[str], *, max_len: int = 240) -> str:
    source = str(text or "")
    if not source.strip():
        return ""
    lowered = source.lower()
    pos = -1
    for term in terms:
        idx = lowered.find(term)
        if idx >= 0:
            pos = idx
            break
    if pos < 0:
        return " ".join(source.split())[:max_len]
    start = max(0, pos - max_len // 3)
    end = min(len(source), start + max_len)
    return " ".join(source[start:end].split())


def _document_from_row(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        filename=row.filename,
        owner_id=row.owner_id,
        blob_uri=row.blob_uri,
        checksum_sha256=row.checksum_sha256,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        status=_coerce_document_status(row.status),
        created_at=row.created_at,
    )


def _llm_parse_result_from_row(row: LLMParseResultRow) -> LLMParseResult:
    normalized_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag in list(row.tags or []):
        normalized = normalize_name(str(tag))
        if not normalized or normalized in seen_tags:
            continue
        seen_tags.add(normalized)
        normalized_tags.append(to_title_case(str(tag)))

    normalized_created_tags: list[str] = []
    seen_created: set[str] = set()
    for tag in list(row.created_tags or []):
        normalized = normalize_name(str(tag))
        if not normalized or normalized in seen_created:
            continue
        seen_created.add(normalized)
        normalized_created_tags.append(to_title_case(str(tag)))
    return LLMParseResult(
        document_id=row.document_id,
        suggested_title=row.suggested_title,
        document_date=row.document_date,
        correspondent=row.correspondent,
        document_type=row.document_type,
        tags=normalized_tags,
        created_correspondent=row.created_correspondent,
        created_document_type=row.created_document_type,
        created_tags=normalized_created_tags,
        created_at=row.created_at,
        llm_details=None,
    )


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, database_url: str) -> None:
        self._engine = build_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._session_factory: Callable = build_session_factory(self._engine)

    def save(self, document: Document) -> None:
        with self._session_factory() as session:
            row = session.get(DocumentRow, document.id)
            if row is None:
                row = DocumentRow(id=document.id)
                session.add(row)
            row.filename = document.filename
            row.owner_id = document.owner_id
            row.blob_uri = document.blob_uri
            row.checksum_sha256 = document.checksum_sha256
            row.content_type = document.content_type
            row.size_bytes = document.size_bytes
            row.status = document.status.value
            row.created_at = document.created_at
            session.commit()

    def get(self, document_id: str) -> Document | None:
        with self._session_factory() as session:
            row = session.get(DocumentRow, document_id)
            if row is None:
                return None
            return _document_from_row(row)

    def get_by_owner_checksum(self, owner_id: str, checksum_sha256: str) -> Document | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(DocumentRow)
                .where(DocumentRow.owner_id == owner_id)
                .where(DocumentRow.checksum_sha256 == checksum_sha256)
                .order_by(DocumentRow.created_at.desc())
                .limit(1)
            )
            if row is None:
                return None
            return _document_from_row(row)

    def list_documents(self, limit: int = 100, *, offset: int = 0) -> list[Document]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentRow)
                .order_by(DocumentRow.created_at.desc())
                .offset(max(0, offset))
                .limit(limit)
            ).all()
            return [_document_from_row(row) for row in rows]

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
        status_values = [status.value for status in statuses] if statuses is not None else None
        with self._session_factory() as session:
            statement = (
                select(DocumentRow, LLMParseResultRow)
                .outerjoin(LLMParseResultRow, LLMParseResultRow.document_id == DocumentRow.id)
                .where(DocumentRow.owner_id == owner_id)
            )
            if status_values is not None:
                statement = statement.where(DocumentRow.status.in_(status_values))
            rows = session.execute(
                statement
                .order_by(DocumentRow.created_at.desc())
                .offset(max(0, offset))
                .limit(max(0, limit))
            ).all()
            return [
                (
                    _document_from_row(document_row),
                    _llm_parse_result_from_row(llm_row) if llm_row is not None else None,
                )
                for document_row, llm_row in rows
            ]

    def count_owner_documents_by_statuses(
        self,
        *,
        owner_id: str,
        statuses: set[DocumentStatus],
    ) -> int:
        if not statuses:
            return 0
        status_values = [status.value for status in statuses]
        with self._session_factory() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(DocumentRow)
                    .where(DocumentRow.owner_id == owner_id)
                    .where(DocumentRow.status.in_(status_values))
                )
                or 0
            )

    def delete_document(self, document_id: str) -> None:
        with self._session_factory() as session:
            collection_rows = session.scalars(
                select(CollectionDocumentRow).where(CollectionDocumentRow.document_id == document_id)
            ).all()
            touched_collection_ids = {row.collection_id for row in collection_rows}
            for row in collection_rows:
                session.delete(row)
            if touched_collection_ids:
                touched_collections = session.scalars(
                    select(CollectionRow).where(CollectionRow.id.in_(sorted(touched_collection_ids)))
                ).all()
                now = datetime.now(UTC)
                for row in touched_collections:
                    row.updated_at = now

            parse_row = session.get(ParseResultRow, document_id)
            if parse_row is not None:
                session.delete(parse_row)

            llm_row = session.get(LLMParseResultRow, document_id)
            if llm_row is not None:
                session.delete(llm_row)

            history_rows = session.scalars(
                select(DocumentHistoryEventRow).where(DocumentHistoryEventRow.document_id == document_id)
            ).all()
            for row in history_rows:
                session.delete(row)

            chunk_rows = session.scalars(
                select(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
            ).all()
            for row in chunk_rows:
                session.delete(row)

            document_row = session.get(DocumentRow, document_id)
            if document_row is not None:
                session.delete(document_row)
            session.commit()

    def save_parse_result(self, result: ParseResult) -> None:
        with self._session_factory() as session:
            row = session.get(ParseResultRow, result.document_id)
            if row is None:
                row = ParseResultRow(document_id=result.document_id)
                session.add(row)
            row.parser = result.parser
            row.status = result.status
            row.size_bytes = result.size_bytes
            row.page_count = result.page_count
            row.text_preview = result.text_preview
            row.created_at = result.created_at
            session.commit()

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        with self._session_factory() as session:
            row = session.get(ParseResultRow, document_id)
            if row is None:
                return None
            return ParseResult(
                document_id=row.document_id,
                parser=row.parser,
                status=row.status,
                size_bytes=row.size_bytes,
                page_count=row.page_count,
                text_preview=row.text_preview,
                created_at=row.created_at,
                ocr_details=None,
            )

    def save_llm_parse_result(self, result: LLMParseResult) -> None:
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

        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, result.document_id)
            if row is None:
                row = LLMParseResultRow(document_id=result.document_id)
                session.add(row)
            row.suggested_title = result.suggested_title
            row.document_date = result.document_date
            row.correspondent = result.correspondent
            row.document_type = result.document_type
            row.tags = normalized_tags
            row.created_correspondent = result.created_correspondent
            row.created_document_type = result.created_document_type
            row.created_tags = normalized_created_tags
            row.created_at = result.created_at
            session.commit()

    def get_llm_parse_result(self, document_id: str) -> LLMParseResult | None:
        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, document_id)
            if row is None:
                return None
            return _llm_parse_result_from_row(row)

    def list_correspondents(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(CorrespondentRow).order_by(CorrespondentRow.name)).all()
            return [row.name for row in rows]

    def list_document_types(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(DocumentTypeRow).order_by(DocumentTypeRow.name)).all()
            return [row.name for row in rows]

    def list_tags(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(TagRow).order_by(TagRow.name)).all()
            by_norm: dict[str, str] = {}
            for row in rows:
                normalized = normalize_name(row.name)
                if not normalized:
                    continue
                by_norm[normalized] = to_title_case(row.name)
            return sorted(by_norm.values())

    def list_tag_stats(self) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(select(LLMParseResultRow)).all()
            return tag_stats_from_metadata(rows)

    def list_owner_tag_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(LLMParseResultRow)
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
            ).all()
            return tag_stats_from_metadata(rows)

    def list_owner_document_type_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(LLMParseResultRow)
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
            ).all()
            return document_type_stats_from_metadata(rows)

    def list_owner_correspondent_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(LLMParseResultRow)
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
            ).all()
            return correspondent_stats_from_metadata(rows)

    def add_correspondent(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        with self._session_factory() as session:
            if session.get(CorrespondentRow, cleaned) is None:
                session.add(CorrespondentRow(name=cleaned))
                session.commit()

    def add_document_type(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        with self._session_factory() as session:
            if session.get(DocumentTypeRow, cleaned) is None:
                session.add(DocumentTypeRow(name=cleaned))
                session.commit()

    def add_tags(self, names: list[str]) -> None:
        cleaned_names = [to_title_case(name) for name in names if name.strip()]
        if not cleaned_names:
            return
        with self._session_factory() as session:
            existing_rows = session.scalars(select(TagRow)).all()
            existing_by_norm = {normalize_name(row.name): row.name for row in existing_rows}
            for name in cleaned_names:
                normalized = normalize_name(name)
                if not normalized or normalized in existing_by_norm:
                    continue
                session.add(TagRow(name=name))
                existing_by_norm[normalized] = name
            session.commit()

    def append_history_events(self, events: list[DocumentHistoryEvent]) -> None:
        if not events:
            return
        with self._session_factory() as session:
            for event in events:
                session.add(
                    DocumentHistoryEventRow(
                        id=event.id,
                        document_id=event.document_id,
                        event_type=event.event_type.value,
                        actor_type=event.actor_type.value,
                        actor_id=event.actor_id,
                        source=event.source,
                        changes=event.changes,
                        created_at=event.created_at,
                    )
                )
            session.commit()

    def list_history(
        self,
        document_id: str,
        *,
        limit: int = 100,
    ) -> list[DocumentHistoryEvent]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentHistoryEventRow)
                .where(DocumentHistoryEventRow.document_id == document_id)
                .order_by(DocumentHistoryEventRow.created_at.desc())
                .limit(limit)
            ).all()
            return [
                DocumentHistoryEvent(
                    id=row.id,
                    document_id=row.document_id,
                    event_type=HistoryEventType(row.event_type),
                    actor_type=HistoryActorType(row.actor_type),
                    actor_id=row.actor_id,
                    source=row.source,
                    changes=dict(row.changes or {}),
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def save_user(self, user: User) -> None:
        with self._session_factory() as session:
            row = session.get(UserRow, user.id)
            if row is None:
                row = UserRow(id=user.id)
                session.add(row)
            row.email = user.email.strip().lower()
            row.full_name = user.full_name
            row.password_hash = user.password_hash
            row.is_active = user.is_active
            row.created_at = user.created_at
            session.commit()

    def get_user(self, user_id: str) -> User | None:
        with self._session_factory() as session:
            row = session.get(UserRow, user_id)
            if row is None:
                return None
            return User(
                id=row.id,
                email=row.email,
                full_name=row.full_name,
                password_hash=row.password_hash,
                is_active=row.is_active,
                created_at=row.created_at,
            )

    def get_user_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        with self._session_factory() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == normalized))
            if row is None:
                return None
            return User(
                id=row.id,
                email=row.email,
                full_name=row.full_name,
                password_hash=row.password_hash,
                is_active=row.is_active,
                created_at=row.created_at,
            )

    def list_users(self, limit: int = 100) -> list[User]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(UserRow).order_by(UserRow.created_at.desc()).limit(limit)
            ).all()
            return [
                User(
                    id=row.id,
                    email=row.email,
                    full_name=row.full_name,
                    password_hash=row.password_hash,
                    is_active=row.is_active,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def save_user_preference(self, preference: UserPreference) -> None:
        with self._session_factory() as session:
            row = session.get(UserPreferenceRow, preference.user_id)
            if row is None:
                row = UserPreferenceRow(user_id=preference.user_id)
                session.add(row)
            row.preferences = dict(preference.preferences or {})
            session.commit()

    def get_user_preference(self, user_id: str) -> UserPreference | None:
        with self._session_factory() as session:
            row = session.get(UserPreferenceRow, user_id)
            if row is None:
                return None
            return UserPreference(
                user_id=row.user_id,
                preferences=dict(row.preferences or {}),
            )

    def save_chat_thread(self, thread: ChatThread) -> None:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread.id)
            if row is None:
                row = ChatThreadRow(id=thread.id)
                session.add(row)
            row.owner_id = thread.owner_id
            row.title = thread.title
            row.messages = [dict(message) for message in thread.messages]
            row.token_usage = dict(thread.token_usage or {})
            row.created_at = thread.created_at
            row.updated_at = thread.updated_at
            session.commit()

    def get_chat_thread(self, owner_id: str, thread_id: str) -> ChatThread | None:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread_id)
            if row is None or row.owner_id != owner_id:
                return None
            return ChatThread(
                id=row.id,
                owner_id=row.owner_id,
                title=row.title,
                messages=[dict(message) for message in list(row.messages or []) if isinstance(message, dict)],
                token_usage=dict(row.token_usage or {}),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def list_chat_threads(self, owner_id: str, limit: int = 20) -> list[ChatThread]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ChatThreadRow)
                .where(ChatThreadRow.owner_id == owner_id)
                .order_by(ChatThreadRow.updated_at.desc())
                .limit(max(0, limit))
            ).all()
            return [
                ChatThread(
                    id=row.id,
                    owner_id=row.owner_id,
                    title=row.title,
                    messages=[dict(message) for message in list(row.messages or []) if isinstance(message, dict)],
                    token_usage=dict(row.token_usage or {}),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]

    def delete_chat_thread(self, owner_id: str, thread_id: str) -> bool:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread_id)
            if row is None or row.owner_id != owner_id:
                return False
            session.delete(row)
            session.commit()
            return True

    def create_collection(self, collection: Collection) -> None:
        with self._session_factory() as session:
            row = session.get(CollectionRow, collection.id)
            if row is None:
                row = CollectionRow(id=collection.id)
                session.add(row)
            row.owner_id = collection.owner_id
            row.name = collection.name
            row.description = collection.description
            row.created_at = collection.created_at
            row.updated_at = collection.updated_at
            session.commit()

    def get_collection(self, collection_id: str) -> Collection | None:
        with self._session_factory() as session:
            row = session.get(CollectionRow, collection_id)
            if row is None:
                return None
            return Collection(
                id=row.id,
                owner_id=row.owner_id,
                name=row.name,
                description=row.description or "",
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def list_collections(self, owner_id: str) -> list[Collection]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(CollectionRow)
                .where(CollectionRow.owner_id == owner_id)
                .order_by(CollectionRow.updated_at.desc())
            ).all()
            return [
                Collection(
                    id=row.id,
                    owner_id=row.owner_id,
                    name=row.name,
                    description=row.description or "",
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]

    def delete_collection(self, collection_id: str) -> None:
        with self._session_factory() as session:
            doc_rows = session.scalars(
                select(CollectionDocumentRow).where(CollectionDocumentRow.collection_id == collection_id)
            ).all()
            for row in doc_rows:
                session.delete(row)
            row = session.get(CollectionRow, collection_id)
            if row is not None:
                session.delete(row)
            session.commit()

    def add_collection_documents(
        self,
        collection_id: str,
        document_ids: list[str],
        *,
        added_at: datetime,
    ) -> None:
        unique_ids = sorted(set(document_ids))
        with self._session_factory() as session:
            existing = session.scalars(
                select(CollectionDocumentRow).where(CollectionDocumentRow.collection_id == collection_id)
            ).all()
            existing_ids = {row.document_id for row in existing}
            for document_id in unique_ids:
                if document_id in existing_ids:
                    continue
                session.add(
                    CollectionDocumentRow(
                        collection_id=collection_id,
                        document_id=document_id,
                        added_at=added_at,
                    )
                )
            row = session.get(CollectionRow, collection_id)
            if row is not None:
                row.updated_at = datetime.now(UTC)
            session.commit()

    def remove_collection_document(self, collection_id: str, document_id: str) -> None:
        with self._session_factory() as session:
            row = session.get(CollectionDocumentRow, {"collection_id": collection_id, "document_id": document_id})
            if row is not None:
                session.delete(row)
            collection = session.get(CollectionRow, collection_id)
            if collection is not None:
                collection.updated_at = datetime.now(UTC)
            session.commit()

    def list_collection_document_ids(self, collection_id: str) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(CollectionDocumentRow)
                .where(CollectionDocumentRow.collection_id == collection_id)
                .order_by(CollectionDocumentRow.document_id.asc())
            ).all()
            return [row.document_id for row in rows]

    def search_documents(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[DocumentSearchHit]:
        terms = _tokenize_query(query)
        if not terms:
            return []
        scoped_ids = sorted(set(document_ids or []))
        has_scope = document_ids is not None
        with self._session_factory() as session:
            query_stmt = select(DocumentRow).where(DocumentRow.owner_id == owner_id)
            if has_scope:
                if not scoped_ids:
                    return []
                query_stmt = query_stmt.where(DocumentRow.id.in_(scoped_ids))
            doc_rows = session.scalars(query_stmt.order_by(DocumentRow.created_at.desc())).all()
            if not doc_rows:
                return []
            ids = [row.id for row in doc_rows]
            parse_rows = session.scalars(select(ParseResultRow).where(ParseResultRow.document_id.in_(ids))).all()
            llm_rows = session.scalars(select(LLMParseResultRow).where(LLMParseResultRow.document_id.in_(ids))).all()
            parse_by_id = {row.document_id: row for row in parse_rows}
            llm_by_id = {row.document_id: row for row in llm_rows}

            hits: list[DocumentSearchHit] = []
            for row in doc_rows:
                parse_row = parse_by_id.get(row.id)
                llm_row = llm_by_id.get(row.id)
                searchable_parts = [
                    row.filename or "",
                    parse_row.text_preview if parse_row is not None else "",
                    llm_row.suggested_title if llm_row is not None else "",
                    llm_row.correspondent if llm_row is not None else "",
                    llm_row.document_type if llm_row is not None else "",
                    " ".join(llm_row.tags or []) if llm_row is not None else "",
                ]
                searchable_text = " ".join(part for part in searchable_parts if part).strip()
                lowered = searchable_text.lower()
                matched = [term for term in terms if term in lowered]
                if not matched:
                    continue
                score = float(sum(lowered.count(term) for term in matched))
                snippet = _extract_snippet(
                    parse_row.text_preview if parse_row is not None else searchable_text,
                    matched,
                )
                hits.append(
                    DocumentSearchHit(
                        document=Document(
                            id=row.id,
                            filename=row.filename,
                            owner_id=row.owner_id,
                            blob_uri=row.blob_uri,
                            checksum_sha256=row.checksum_sha256,
                            content_type=row.content_type,
                            size_bytes=row.size_bytes,
                            status=_coerce_document_status(row.status),
                            created_at=row.created_at,
                        ),
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
        with self._session_factory() as session:
            existing = session.scalars(
                select(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
            ).all()
            for row in existing:
                session.delete(row)
            for chunk in chunks:
                session.add(
                    DocumentChunkRow(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        owner_id=chunk.owner_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        created_at=chunk.created_at,
                    )
                )
            session.commit()

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentChunkRow)
                .where(DocumentChunkRow.document_id == document_id)
                .order_by(DocumentChunkRow.chunk_index.asc())
            ).all()
            return [
                DocumentChunk(
                    id=row.id,
                    document_id=row.document_id,
                    owner_id=row.owner_id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    token_count=row.token_count,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def search_document_chunks(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 40,
        document_ids: list[str] | None = None,
    ) -> list[DocumentChunkSearchHit]:
        terms = _tokenize_query(query)
        if not terms:
            return []
        scoped_ids = sorted(set(document_ids or []))
        has_scope = document_ids is not None
        with self._session_factory() as session:
            stmt = select(DocumentChunkRow).where(DocumentChunkRow.owner_id == owner_id)
            if has_scope:
                if not scoped_ids:
                    return []
                stmt = stmt.where(DocumentChunkRow.document_id.in_(scoped_ids))
            rows = session.scalars(stmt.order_by(DocumentChunkRow.created_at.desc())).all()
            hits: list[DocumentChunkSearchHit] = []
            for row in rows:
                lowered = str(row.content or "").lower()
                matched = [term for term in terms if term in lowered]
                if not matched:
                    continue
                score = float(sum(lowered.count(term) for term in matched))
                hits.append(
                    DocumentChunkSearchHit(
                        chunk=DocumentChunk(
                            id=row.id,
                            document_id=row.document_id,
                            owner_id=row.owner_id,
                            chunk_index=row.chunk_index,
                            content=row.content,
                            token_count=row.token_count,
                            created_at=row.created_at,
                        ),
                        score=score,
                        matched_terms=matched,
                    )
                )
            hits.sort(key=lambda item: (item.score, item.chunk.created_at, item.chunk.chunk_index), reverse=True)
            return hits[: max(1, limit)]
