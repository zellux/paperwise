from typing import Protocol

from zapis.domain.models import Document, ParseResult


class OCRProvider(Protocol):
    def extract_text(self, uri: str) -> str:
        """Extract text from a document object URI."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Create an embedding for an input text."""


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate an answer from prompt context."""


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

    def save_parse_result(self, result: ParseResult) -> None:
        """Persist parse output for a document."""

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        """Load parse output by document ID."""


class IngestionDispatcher(Protocol):
    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Dispatch ingestion work and return a job identifier."""
