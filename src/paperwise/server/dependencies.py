from fastapi import Cookie, Depends, Header, HTTPException, status

from paperwise.application.services.auth_tokens import decode_access_token
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

_ingestion_dispatcher: IngestionDispatcher = CeleryIngestionDispatcher()
_settings = get_settings()
_document_repository: DocumentRepository
if _settings.repository_backend.lower() == "postgres":
    _document_repository = PostgresDocumentRepository(_settings.postgres_url)
else:
    _document_repository = InMemoryDocumentRepository()
_storage: StorageProvider = LocalStorageAdapter(_settings.object_store_root)
_llm_provider: LLMProvider = MissingOpenAIProvider()
SESSION_COOKIE_NAME = "paperwise_session"


def settings_dependency() -> Settings:
    return _settings


def document_repository_dependency() -> DocumentRepository:
    return _document_repository


def ingestion_dispatcher_dependency() -> IngestionDispatcher:
    return _ingestion_dispatcher


def storage_dependency() -> StorageProvider:
    return _storage


def llm_provider_dependency() -> LLMProvider:
    return _llm_provider


def current_user_dependency(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> User:
    token = ""
    if session_token:
        token = session_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_access_token(token=token, secret=_settings.auth_secret)
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
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> User | None:
    try:
        return current_user_dependency(
            authorization=authorization,
            session_token=session_token,
            repository=repository,
        )
    except HTTPException:
        return None
