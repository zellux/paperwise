from paperwise.domain.models import (
    Document,
    DocumentHistoryEvent,
    DocumentIndexState,
    LLMParseResult,
    ParseResult,
)
from paperwise.application.services.document_indexing import effective_document_index_status
from paperwise.server.schemas.documents import (
    DocumentDetailResponse,
    DocumentHistoryEventResponse,
    DocumentIndexStateResponse,
    DocumentListItemResponse,
    DocumentListMetadata,
    DocumentResponse,
    LLMParseResultResponse,
    ParseResultResponse,
)


def present_document(
    document: Document,
    index_state: DocumentIndexState | None = None,
) -> DocumentResponse:
    payload = DocumentResponse.model_validate(document).model_dump()
    payload["index_status"] = effective_document_index_status(document=document, state=index_state)
    return DocumentResponse(**payload)


def present_document_list_metadata(result: LLMParseResult | None) -> DocumentListMetadata | None:
    if result is None:
        return None
    return DocumentListMetadata.model_validate(result)


def present_document_list_item(
    *,
    document: Document,
    llm_result: LLMParseResult | None = None,
    index_state: DocumentIndexState | None = None,
) -> DocumentListItemResponse:
    base = present_document(document, index_state).model_dump()
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


def present_document_index_state(
    *,
    document: Document,
    index_state: DocumentIndexState | None,
) -> DocumentIndexStateResponse:
    if index_state is None:
        return DocumentIndexStateResponse(document_id=document.id, status="not_indexed")
    return DocumentIndexStateResponse(
        document_id=index_state.document_id,
        status=effective_document_index_status(document=document, state=index_state),
        index_version=index_state.index_version,
        source_checksum=index_state.source_checksum,
        chunk_count=index_state.chunk_count,
        updated_at=index_state.updated_at,
        indexed_at=index_state.indexed_at,
        last_error=index_state.last_error,
    )


def present_document_detail(
    *,
    document: Document,
    llm_result: LLMParseResult | None,
    parse_result: ParseResult | None,
    index_state: DocumentIndexState | None = None,
) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        document=present_document(document, index_state),
        index=present_document_index_state(document=document, index_state=index_state),
        llm_metadata=present_document_list_metadata(llm_result),
        ocr_text_preview=parse_result.text_preview if parse_result is not None else None,
        ocr_parsed_at=parse_result.created_at if parse_result is not None else None,
    )
