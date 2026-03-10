from paperwise.domain.models import UserPreference
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.workers.tasks import _resolve_ocr_provider_for_owner


def test_resolve_ocr_provider_defaults_to_llm_without_preferences() -> None:
    repository = InMemoryDocumentRepository()
    assert _resolve_ocr_provider_for_owner(repository, "user-1") == "llm"


def test_resolve_ocr_provider_reads_saved_preference() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_provider": "tesseract"})
    )
    assert _resolve_ocr_provider_for_owner(repository, "user-1") == "tesseract"


def test_resolve_ocr_provider_falls_back_to_llm_for_invalid_value() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_provider": "unknown-provider"})
    )
    assert _resolve_ocr_provider_for_owner(repository, "user-1") == "llm"
