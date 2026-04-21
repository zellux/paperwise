from datetime import datetime
from typing import Any, Protocol

from paperwise.domain.models import (
    Collection,
    DocumentChunk,
    DocumentChunkSearchHit,
    Document,
    DocumentSearchHit,
    DocumentHistoryEvent,
    LLMParseResult,
    ParseResult,
    UserPreference,
    User,
)


class OCRProvider(Protocol):
    def extract_text(self, uri: str) -> str:
        """Extract text from a document object URI."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Create an embedding for an input text."""


class LLMProvider(Protocol):
    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        """Extract OCR text from a document preview using OCR-specific prompting."""

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        """Suggest document metadata fields from parsed text and taxonomy context."""

    def answer_grounded(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Answer a question strictly from provided contexts with citations."""

    def rewrite_retrieval_queries(
        self,
        *,
        question: str,
    ) -> dict[str, Any]:
        """Generate retrieval query variants and anchors for grounded retrieval."""


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Run a retrieval query and return result documents/chunks."""


class StorageProvider(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store a binary artifact and return its canonical URI."""

    def delete(self, uri: str) -> None:
        """Delete a previously stored artifact if it exists."""


class DocumentRepository(Protocol):
    def save(self, document: Document) -> None:
        """Persist a document aggregate."""

    def get(self, document_id: str) -> Document | None:
        """Load a document by ID."""

    def get_by_owner_checksum(self, owner_id: str, checksum_sha256: str) -> Document | None:
        """Find an existing document by owner + SHA256 checksum."""

    def list_documents(self, limit: int = 100, *, offset: int = 0) -> list[Document]:
        """List recent documents."""

    def delete_document(self, document_id: str) -> None:
        """Delete a document and all related records."""

    def save_parse_result(self, result: ParseResult) -> None:
        """Persist parse output for a document."""

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        """Load parse output by document ID."""

    def save_llm_parse_result(self, result: LLMParseResult) -> None:
        """Persist LLM metadata parse output for a document."""

    def get_llm_parse_result(self, document_id: str) -> LLMParseResult | None:
        """Load LLM metadata parse output for a document."""

    def list_correspondents(self) -> list[str]:
        """Return known correspondent names."""

    def list_document_types(self) -> list[str]:
        """Return known document type names."""

    def list_tags(self) -> list[str]:
        """Return known tag names."""

    def list_tag_stats(self) -> list[tuple[str, int]]:
        """Return tag usage counts as (tag_name, document_count)."""

    def add_correspondent(self, name: str) -> None:
        """Add a correspondent if missing."""

    def add_document_type(self, name: str) -> None:
        """Add a document type if missing."""

    def add_tags(self, names: list[str]) -> None:
        """Add tag names if missing."""

    def append_history_events(self, events: list[DocumentHistoryEvent]) -> None:
        """Append one or more immutable document history events."""

    def list_history(
        self,
        document_id: str,
        *,
        limit: int = 100,
    ) -> list[DocumentHistoryEvent]:
        """Return document history entries ordered newest-first."""

    def save_user(self, user: User) -> None:
        """Persist a user."""

    def get_user(self, user_id: str) -> User | None:
        """Load a user by ID."""

    def get_user_by_email(self, email: str) -> User | None:
        """Load a user by email."""

    def list_users(self, limit: int = 100) -> list[User]:
        """List users ordered newest-first."""

    def save_user_preference(self, preference: UserPreference) -> None:
        """Persist user preferences payload."""

    def get_user_preference(self, user_id: str) -> UserPreference | None:
        """Load user preferences by user ID."""

    def create_collection(self, collection: Collection) -> None:
        """Persist a user-owned collection."""

    def get_collection(self, collection_id: str) -> Collection | None:
        """Load a collection by ID."""

    def list_collections(self, owner_id: str) -> list[Collection]:
        """List collections for a user."""

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection and its document memberships."""

    def add_collection_documents(
        self,
        collection_id: str,
        document_ids: list[str],
        *,
        added_at: datetime,
    ) -> None:
        """Add one or more documents to a collection."""

    def remove_collection_document(self, collection_id: str, document_id: str) -> None:
        """Remove one document from a collection."""

    def list_collection_document_ids(self, collection_id: str) -> list[str]:
        """Return document IDs contained in a collection."""

    def search_documents(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[DocumentSearchHit]:
        """Run keyword search over owner-visible documents (optionally scoped to IDs)."""

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        owner_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        """Replace indexed chunks for one document."""

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        """List indexed chunks for one document."""

    def search_document_chunks(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 40,
        document_ids: list[str] | None = None,
    ) -> list[DocumentChunkSearchHit]:
        """Run keyword chunk search over owner-visible chunks (optionally scoped)."""


class IngestionDispatcher(Protocol):
    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Dispatch ingestion work and return a job identifier."""
