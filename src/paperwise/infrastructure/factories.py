from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.infrastructure.config import Settings
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)


def build_document_repository(settings: Settings) -> DocumentRepository:
    if settings.repository_backend.lower() == "postgres":
        return PostgresDocumentRepository(settings.postgres_url)
    return InMemoryDocumentRepository()


def build_llm_provider(settings: Settings) -> LLMProvider | None:
    del settings
    return None
