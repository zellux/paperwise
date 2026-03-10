from collections.abc import Callable

from sqlalchemy import select

from zapis.application.interfaces import DocumentRepository
from zapis.domain.models import (
    Document,
    DocumentHistoryEvent,
    DocumentStatus,
    HistoryActorType,
    HistoryEventType,
    LLMParseResult,
    ParseResult,
)
from zapis.infrastructure.db import Base, build_engine, build_session_factory
from zapis.infrastructure.repositories.postgres_models import (
    CorrespondentRow,
    DocumentRow,
    DocumentHistoryEventRow,
    DocumentTypeRow,
    LLMParseResultRow,
    ParseResultRow,
    TagRow,
)


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

    def list_documents(self, limit: int = 100) -> list[Document]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentRow).order_by(DocumentRow.created_at.desc()).limit(limit)
            ).all()
            return [
                Document(
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
                for row in rows
            ]

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
            )

    def save_llm_parse_result(self, result: LLMParseResult) -> None:
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
            normalized_tags: list[str] = []
            seen_tags: set[str] = set()
            for tag in list(row.tags or []):
                normalized = _normalize_name(str(tag))
                if not normalized or normalized in seen_tags:
                    continue
                seen_tags.add(normalized)
                normalized_tags.append(_to_title_case(str(tag)))

            normalized_created_tags: list[str] = []
            seen_created: set[str] = set()
            for tag in list(row.created_tags or []):
                normalized = _normalize_name(str(tag))
                if not normalized or normalized in seen_created:
                    continue
                seen_created.add(normalized)
                normalized_created_tags.append(_to_title_case(str(tag)))
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
            )

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
                normalized = _normalize_name(row.name)
                if not normalized:
                    continue
                by_norm[normalized] = _to_title_case(row.name)
            return sorted(by_norm.values())

    def list_tag_stats(self) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(select(LLMParseResultRow)).all()
            counts: dict[str, int] = {}
            display_name_by_key: dict[str, str] = {}
            for row in rows:
                seen: set[str] = set()
                for tag in list(row.tags or []):
                    cleaned = str(tag).strip()
                    if not cleaned:
                        continue
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
        cleaned_names = [_to_title_case(name) for name in names if name.strip()]
        if not cleaned_names:
            return
        with self._session_factory() as session:
            existing_rows = session.scalars(select(TagRow)).all()
            existing_by_norm = {_normalize_name(row.name): row.name for row in existing_rows}
            for name in cleaned_names:
                normalized = _normalize_name(name)
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
