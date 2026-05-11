from paperwise.domain.models import Document, DocumentHistoryEvent, LLMParseResult
from paperwise.server.presenters.documents import (
    present_document_history_event,
    present_document_list_item,
)


def document_list_item(document: Document, llm_result: LLMParseResult | None) -> dict:
    return present_document_list_item(
        document=document,
        llm_result=llm_result,
    ).model_dump(mode="json")


def history_event_item(event: DocumentHistoryEvent) -> dict:
    return present_document_history_event(event).model_dump(mode="json")
