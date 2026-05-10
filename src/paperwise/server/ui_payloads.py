from paperwise.domain.models import Document, DocumentHistoryEvent, LLMParseResult
from paperwise.server.document_responses import (
    DocumentHistoryEventResponse,
    DocumentListItemResponse,
)


def document_list_item(document: Document, llm_result: LLMParseResult | None) -> dict:
    return DocumentListItemResponse.from_domain(
        document=document,
        llm_result=llm_result,
    ).model_dump(mode="json")


def history_event_item(event: DocumentHistoryEvent) -> dict:
    return DocumentHistoryEventResponse.from_domain(event).model_dump(mode="json")
