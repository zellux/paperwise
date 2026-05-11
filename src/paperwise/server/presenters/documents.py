from paperwise.domain.models import Document, DocumentHistoryEvent, LLMParseResult, ParseResult
from paperwise.server.schemas.documents import (
    DocumentDetailResponse,
    DocumentHistoryEventResponse,
    DocumentListItemResponse,
    DocumentListMetadata,
    DocumentResponse,
    LLMParseResultResponse,
    ParseResultResponse,
)


def present_document(document: Document) -> DocumentResponse:
    return DocumentResponse.model_validate(document)


def present_document_list_metadata(result: LLMParseResult | None) -> DocumentListMetadata | None:
    if result is None:
        return None
    return DocumentListMetadata.model_validate(result)


def present_document_list_item(
    *,
    document: Document,
    llm_result: LLMParseResult | None = None,
) -> DocumentListItemResponse:
    base = present_document(document).model_dump()
    return DocumentListItemResponse(
        **base,
        llm_metadata=present_document_list_metadata(llm_result),
    )


def present_parse_result(result: ParseResult) -> ParseResultResponse:
    return ParseResultResponse.model_validate(result)


def present_llm_parse_result(result: LLMParseResult) -> LLMParseResultResponse:
    return LLMParseResultResponse.model_validate(result)


def present_document_history_event(event: DocumentHistoryEvent) -> DocumentHistoryEventResponse:
    return DocumentHistoryEventResponse.model_validate(event)


def present_document_detail(
    *,
    document: Document,
    llm_result: LLMParseResult | None,
    parse_result: ParseResult | None,
) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        document=present_document(document),
        llm_metadata=present_document_list_metadata(llm_result),
        ocr_text_preview=parse_result.text_preview if parse_result is not None else None,
        ocr_parsed_at=parse_result.created_at if parse_result is not None else None,
    )
