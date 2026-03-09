from collections.abc import Callable

from sqlalchemy import select

from zapis.application.interfaces import DocumentRepository
from zapis.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult
from zapis.infrastructure.db import Base, build_engine, build_session_factory
from zapis.infrastructure.repositories.postgres_models import (
    CorrespondentRow,
    DocumentRow,
    DocumentTypeRow,
    LLMParseResultRow,
    ParseResultRow,
    TagRow,
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
            return Document(
                id=row.id,
                filename=row.filename,
                owner_id=row.owner_id,
                blob_uri=row.blob_uri,
                checksum_sha256=row.checksum_sha256,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
                status=DocumentStatus(row.status),
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
                    status=DocumentStatus(row.status),
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
        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, result.document_id)
            if row is None:
                row = LLMParseResultRow(document_id=result.document_id)
                session.add(row)
            row.suggested_title = result.suggested_title
            row.document_date = result.document_date
            row.correspondent = result.correspondent
            row.document_type = result.document_type
            row.tags = result.tags
            row.created_correspondent = result.created_correspondent
            row.created_document_type = result.created_document_type
            row.created_tags = result.created_tags
            row.created_at = result.created_at
            session.commit()

    def get_llm_parse_result(self, document_id: str) -> LLMParseResult | None:
        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, document_id)
            if row is None:
                return None
            return LLMParseResult(
                document_id=row.document_id,
                suggested_title=row.suggested_title,
                document_date=row.document_date,
                correspondent=row.correspondent,
                document_type=row.document_type,
                tags=list(row.tags or []),
                created_correspondent=row.created_correspondent,
                created_document_type=row.created_document_type,
                created_tags=list(row.created_tags or []),
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
            return [row.name for row in rows]

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
        cleaned_names = [name.strip() for name in names if name.strip()]
        if not cleaned_names:
            return
        with self._session_factory() as session:
            for name in cleaned_names:
                if session.get(TagRow, name) is None:
                    session.add(TagRow(name=name))
            session.commit()
