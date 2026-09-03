from paperwise.domain.models import (
    Document,
    DocumentHistoryEvent,
    DocumentIndexState,
    LLMParseResult,
    ParseResult,
)
from paperwise.server.presenters.documents import (
    present_document_history_event,
    present_document_list_item,
)


def document_list_item(
    document: Document,
    llm_result: LLMParseResult | None,
    parse_result: ParseResult | None = None,
    index_state: DocumentIndexState | None = None,
) -> dict:
    item = present_document_list_item(
        document=document,
        llm_result=llm_result,
        index_state=index_state,
    ).model_dump(mode="json")
    if parse_result is not None:
        item["page_count"] = parse_result.page_count
    return item


def history_event_item(event: DocumentHistoryEvent) -> dict:
    return present_document_history_event(event).model_dump(mode="json")
