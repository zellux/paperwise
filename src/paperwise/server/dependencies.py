from functools import lru_cache

from fastapi import Cookie, Depends, HTTPException, status

from paperwise.application.services.session_tokens import decode_session_token
from paperwise.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    LLMProvider,
    StorageProvider,
)
from paperwise.domain.models import User
from paperwise.infrastructure.config import Settings, get_settings
from paperwise.infrastructure.dispatchers.celery_ingestion_dispatcher import (
    CeleryIngestionDispatcher,
)
from paperwise.infrastructure.llm.missing_openai_provider import MissingOpenAIProvider
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from paperwise.infrastructure.storage.local_storage import LocalStorageAdapter

SESSION_COOKIE_NAME = "paperwise_session"


@lru_cache
def settings_dependency() -> Settings:
    return get_settings()


@lru_cache
def document_repository_dependency() -> DocumentRepository:
    settings = settings_dependency()
    if settings.repository_backend.lower() == "postgres":
        return PostgresDocumentRepository(settings.postgres_url)
    return InMemoryDocumentRepository()


@lru_cache
def ingestion_dispatcher_dependency() -> IngestionDispatcher:
    return CeleryIngestionDispatcher()


@lru_cache
def storage_dependency() -> StorageProvider:
    return LocalStorageAdapter(settings_dependency().object_store_root)


@lru_cache
def llm_provider_dependency() -> LLMProvider:
    return MissingOpenAIProvider()


def current_user_dependency(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> User:
    token = ""
    if session_token:
        token = session_token.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_session_token(token=token, secret=settings.auth_secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = repository.get_user(str(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    return user


def optional_current_user_dependency(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> User | None:
    try:
        return current_user_dependency(
            session_token=session_token,
            repository=repository,
            settings=settings,
        )
    except HTTPException:
        return None
