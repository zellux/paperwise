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

