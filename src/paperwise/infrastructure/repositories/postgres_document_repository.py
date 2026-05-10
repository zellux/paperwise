from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, select

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.search_text import extract_search_snippet, tokenize_search_query
from paperwise.domain.models import (
    DocumentChunk,
    DocumentChunkSearchHit,
    Document,
    DocumentSearchHit,
    DocumentStatus,
    LLMParseResult,
)
from paperwise.infrastructure.db import Base, build_engine, build_session_factory
from paperwise.infrastructure.repositories.postgres_chat_thread_repository import (
    PostgresChatThreadRepositoryMixin,
)
from paperwise.infrastructure.repositories.postgres_collection_repository import (
    PostgresCollectionRepositoryMixin,
)
from paperwise.infrastructure.repositories.postgres_history_repository import PostgresHistoryRepositoryMixin
from paperwise.infrastructure.repositories.postgres_parse_result_repository import (
    PostgresParseResultRepositoryMixin,
    llm_parse_result_from_row,
)
from paperwise.infrastructure.repositories.postgres_models import (
    CollectionDocumentRow,
    CollectionRow,
    DocumentRow,
    DocumentChunkRow,
    DocumentHistoryEventRow,
    LLMParseResultRow,
    ParseResultRow,
)
from paperwise.infrastructure.repositories.postgres_taxonomy_repository import PostgresTaxonomyRepositoryMixin
from paperwise.infrastructure.repositories.postgres_user_repository import PostgresUserRepositoryMixin


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


class PostgresDocumentRepository(
    PostgresChatThreadRepositoryMixin,
    PostgresCollectionRepositoryMixin,
    PostgresHistoryRepositoryMixin,
    PostgresParseResultRepositoryMixin,
    PostgresTaxonomyRepositoryMixin,
    PostgresUserRepositoryMixin,
    DocumentRepository,
):
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
                    llm_parse_result_from_row(llm_row) if llm_row is not None else None,
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
                snippet = extract_search_snippet(
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
        terms = tokenize_search_query(query)
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
