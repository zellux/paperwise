from typing import Protocol


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
