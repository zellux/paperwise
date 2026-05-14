from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, inspect, select, text

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.chat_threads import chat_thread_document_references
from paperwise.domain.models import (
    ChatThread,
    Document,
    DocumentStatus,
    LLMParseResult,
)
from paperwise.infrastructure.db import Base, build_engine, build_session_factory
from paperwise.infrastructure.repositories.postgres_chat_thread_repository import (
    PostgresChatThreadRepositoryMixin,
)
from paperwise.infrastructure.repositories.postgres_chunk_repository import PostgresChunkRepositoryMixin
from paperwise.infrastructure.repositories.postgres_collection_repository import (
    PostgresCollectionRepositoryMixin,
)
from paperwise.infrastructure.repositories.postgres_document_mapper import document_from_row
from paperwise.infrastructure.repositories.postgres_history_repository import PostgresHistoryRepositoryMixin
from paperwise.infrastructure.repositories.postgres_parse_result_repository import (
    PostgresParseResultRepositoryMixin,
    llm_parse_result_from_row,
)
from paperwise.infrastructure.repositories.postgres_search_repository import PostgresSearchRepositoryMixin
from paperwise.infrastructure.repositories.postgres_models import (
    ChatThreadDocumentReferenceRow,
    ChatThreadRow,
    CollectionDocumentRow,
    CollectionRow,
    DocumentChunkRow,
    DocumentRow,
    DocumentHistoryEventRow,
    LLMParseResultRow,
    ParseResultRow,
)
from paperwise.infrastructure.repositories.postgres_taxonomy_repository import PostgresTaxonomyRepositoryMixin
from paperwise.infrastructure.repositories.postgres_user_repository import PostgresUserRepositoryMixin


class PostgresDocumentRepository(
    PostgresChatThreadRepositoryMixin,
    PostgresChunkRepositoryMixin,
    PostgresCollectionRepositoryMixin,
    PostgresHistoryRepositoryMixin,
    PostgresParseResultRepositoryMixin,
    PostgresSearchRepositoryMixin,
    PostgresTaxonomyRepositoryMixin,
    PostgresUserRepositoryMixin,
    DocumentRepository,
):
    def __init__(self, database_url: str) -> None:
        self._engine = build_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._ensure_document_schema()
        self._ensure_chat_thread_schema()
        self._session_factory: Callable = build_session_factory(self._engine)
        self._ensure_chat_thread_reference_schema()

    def _ensure_document_schema(self) -> None:
        inspector = inspect(self._engine)
        if "documents" not in inspector.get_table_names():
            return
        column_names = {column["name"] for column in inspector.get_columns("documents")}
        if "starred" in column_names:
            return
        default_value = "0" if self._engine.dialect.name == "sqlite" else "false"
        with self._engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE documents ADD COLUMN starred BOOLEAN NOT NULL DEFAULT {default_value}")
            )

    def _ensure_chat_thread_schema(self) -> None:
        inspector = inspect(self._engine)
        if "chat_threads" not in inspector.get_table_names():
            return
        column_names = {column["name"] for column in inspector.get_columns("chat_threads")}
        if "document_refs_indexed_at" in column_names:
            return
        column_type = "TIMESTAMP" if self._engine.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
        with self._engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE chat_threads ADD COLUMN document_refs_indexed_at {column_type}")
            )

    def _ensure_chat_thread_reference_schema(self) -> None:
        inspector = inspect(self._engine)
        table_names = set(inspector.get_table_names())
        if "chat_thread_document_refs" not in table_names or "chat_threads" not in table_names:
            return
        with self._session_factory() as session:
            thread_rows = session.scalars(
                select(ChatThreadRow).where(ChatThreadRow.document_refs_indexed_at.is_(None))
            ).all()
            indexed_at = datetime.now(UTC)
            for row in thread_rows:
                session.query(ChatThreadDocumentReferenceRow).filter(
                    ChatThreadDocumentReferenceRow.thread_id == row.id
                ).delete(synchronize_session=False)
                thread = ChatThread(
                    id=row.id,
                    owner_id=row.owner_id,
                    title=row.title,
                    messages=[dict(message) for message in list(row.messages or []) if isinstance(message, dict)],
                    token_usage=dict(row.token_usage or {}),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for reference in chat_thread_document_references(thread):
                    session.add(
                        ChatThreadDocumentReferenceRow(
                            thread_id=reference.thread_id,
                            document_id=reference.document_id,
                            owner_id=reference.owner_id,
                            title=reference.title,
                            message_count=reference.message_count,
                            reference_count=reference.reference_count,
                            question=reference.question,
                            source_titles=reference.source_titles,
                            created_at=reference.created_at,
                            updated_at=reference.updated_at,
                        )
                    )
                row.document_refs_indexed_at = indexed_at
            session.commit()

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
            row.starred = bool(document.starred)
            session.commit()

    def get(self, document_id: str) -> Document | None:
        with self._session_factory() as session:
            row = session.get(DocumentRow, document_id)
            if row is None:
                return None
            return document_from_row(row)

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
            return document_from_row(row)

    def list_documents(self, limit: int = 100, *, offset: int = 0) -> list[Document]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentRow)
                .order_by(DocumentRow.created_at.desc())
                .offset(max(0, offset))
                .limit(limit)
            ).all()
            return [document_from_row(row) for row in rows]

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
                    document_from_row(document_row),
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
