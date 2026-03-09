from zapis.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    StorageProvider,
)
from zapis.infrastructure.config import Settings, get_settings
from zapis.infrastructure.dispatchers.celery_ingestion_dispatcher import (
    CeleryIngestionDispatcher,
)
from zapis.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from zapis.infrastructure.storage.local_storage import LocalStorageAdapter

_document_repository: DocumentRepository = InMemoryDocumentRepository()
_ingestion_dispatcher: IngestionDispatcher = CeleryIngestionDispatcher()
_storage: StorageProvider = LocalStorageAdapter(get_settings().object_store_root)


def settings_dependency() -> Settings:
    return get_settings()


def document_repository_dependency() -> DocumentRepository:
    return _document_repository


def ingestion_dispatcher_dependency() -> IngestionDispatcher:
    return _ingestion_dispatcher


def storage_dependency() -> StorageProvider:
    return _storage
