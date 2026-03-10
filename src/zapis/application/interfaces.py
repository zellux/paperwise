from typing import Any, Protocol

from zapis.domain.models import Document, LLMParseResult, ParseResult


class OCRProvider(Protocol):
    def extract_text(self, uri: str) -> str:
        """Extract text from a document object URI."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Create an embedding for an input text."""


class LLMProvider(Protocol):
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        """Suggest document metadata fields from parsed text and taxonomy context."""


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Run a retrieval query and return result documents/chunks."""


class StorageProvider(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store a binary artifact and return its canonical URI."""


class DocumentRepository(Protocol):
    def save(self, document: Document) -> None:
        """Persist a document aggregate."""

    def get(self, document_id: str) -> Document | None:
        """Load a document by ID."""

    def list_documents(self, limit: int = 100) -> list[Document]:
        """List recent documents."""

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


class IngestionDispatcher(Protocol):
    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Dispatch ingestion work and return a job identifier."""
