from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from paperwise.infrastructure.db import Base


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(1024))
    owner_id: Mapped[str] = mapped_column(String(256), index=True)
    blob_uri: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(256))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    starred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)


class ParseResultRow(Base):
    __tablename__ = "parse_results"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parser: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    text_preview: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))


class LLMParseResultRow(Base):
    __tablename__ = "llm_parse_results"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    suggested_title: Mapped[str] = mapped_column(String(1024))
    document_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correspondent: Mapped[str] = mapped_column(String(256), index=True)
    document_type: Mapped[str] = mapped_column(String(256), index=True)
    tags: Mapped[list[str]] = mapped_column(JSON)
    created_correspondent: Mapped[bool]
    created_document_type: Mapped[bool]
    created_tags: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))


class CorrespondentRow(Base):
    __tablename__ = "correspondents"

    name: Mapped[str] = mapped_column(String(256), primary_key=True)


class DocumentTypeRow(Base):
    __tablename__ = "document_types"

    name: Mapped[str] = mapped_column(String(256), primary_key=True)


class TagRow(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(256), primary_key=True)


class DocumentHistoryEventRow(Base):
    __tablename__ = "document_history_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source: Mapped[str] = mapped_column(String(256))
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(256))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool]
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)


class UserPreferenceRow(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSON)


class ChatThreadRow(Base):
    __tablename__ = "chat_threads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256))
    messages: Mapped[list[dict]] = mapped_column(JSON)
    token_usage: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    document_refs_indexed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatThreadDocumentReferenceRow(Base):
    __tablename__ = "chat_thread_document_refs"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256))
    message_count: Mapped[int] = mapped_column(Integer)
    reference_count: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    source_titles: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)


class CollectionRow(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)


class CollectionDocumentRow(Base):
    __tablename__ = "collection_documents"

    collection_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    added_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)


class DocumentChunkRow(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
