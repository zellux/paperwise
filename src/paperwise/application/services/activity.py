from dataclasses import dataclass

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.user_preferences import load_user_preferences
from paperwise.domain.models import Document, DocumentStatus, LLMParseResult


@dataclass(frozen=True)
class ActivitySummary:
    documents: list[tuple[Document, LLMParseResult | None]]
    total_tokens: int


def owner_activity_summary(
    *,
    repository: DocumentRepository,
    owner_id: str,
    limit: int,
) -> ActivitySummary:
    documents = repository.list_owner_documents_with_llm_results(
        owner_id=owner_id,
        limit=limit,
        statuses={DocumentStatus.READY},
    )
    preferences = load_user_preferences(repository=repository, user_id=owner_id)
    return ActivitySummary(
        documents=documents,
        total_tokens=int(preferences.get("llm_total_tokens_processed") or 0),
    )
