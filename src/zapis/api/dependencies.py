from zapis.application.interfaces import DocumentRepository, IngestionDispatcher
from zapis.infrastructure.config import Settings, get_settings
from zapis.infrastructure.dispatchers.celery_ingestion_dispatcher import (
    CeleryIngestionDispatcher,
)
from zapis.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)

_document_repository: DocumentRepository = InMemoryDocumentRepository()
_ingestion_dispatcher: IngestionDispatcher = CeleryIngestionDispatcher()


def settings_dependency() -> Settings:
    return get_settings()


def document_repository_dependency() -> DocumentRepository:
    return _document_repository


def ingestion_dispatcher_dependency() -> IngestionDispatcher:
    return _ingestion_dispatcher
