from datetime import UTC, datetime

from zapis.application.services.llm_parsing import parse_with_llm
from zapis.domain.models import Document, DocumentStatus, ParseResult
from zapis.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)


class FullMetadataLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del existing_correspondents
        del existing_document_types
        del existing_tags
        return {
            "suggested_title": "January Statement",
            "document_date": "2026-01-15",
            "correspondent": "Experian",
            "document_type": "Credit Report",
            "tags": ["Credit", "Identity"],
        }


class PartialMetadataLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del existing_correspondents
        del existing_document_types
        del existing_tags
        # Intentionally missing most keys to ensure we keep previous values.
        return {
            "suggested_title": "January Statement (Reviewed)",
        }


class NullDateLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del existing_correspondents
        del existing_document_types
        del existing_tags
        # Provider included the key, but did not infer a value.
        return {
            "document_date": None,
        }


def _build_document() -> Document:
    return Document(
        id="doc-llm-merge",
        filename="statement.pdf",
        owner_id="user-merge",
        blob_uri="file:///tmp/statement.pdf",
        checksum_sha256="abc123",
        content_type="application/pdf",
        size_bytes=1234,
        status=DocumentStatus.PROCESSING,
        created_at=datetime.now(UTC),
    )


def _build_parse_result(document_id: str) -> ParseResult:
    return ParseResult(
        document_id=document_id,
        parser="mock",
        status="parsed",
        size_bytes=1234,
        page_count=1,
        text_preview="sample",
        created_at=datetime.now(UTC),
    )


def test_parse_with_llm_keeps_previous_fields_when_provider_omits_keys() -> None:
    repository = InMemoryDocumentRepository()
    document = _build_document()
    parse_result = _build_parse_result(document.id)

    first = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=FullMetadataLLMProvider(),
    )
    second = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=PartialMetadataLLMProvider(),
    )

    assert first.suggested_title == "January Statement"
    assert second.suggested_title == "January Statement (Reviewed)"
    # Omitted fields are preserved from the previous metadata result.
    assert second.document_date == first.document_date
    assert second.correspondent == first.correspondent
    assert second.document_type == first.document_type
    assert second.tags == first.tags


def test_parse_with_llm_keeps_previous_date_when_provider_returns_null() -> None:
    repository = InMemoryDocumentRepository()
    document = _build_document()
    parse_result = _build_parse_result(document.id)

    first = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=FullMetadataLLMProvider(),
    )
    second = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=NullDateLLMProvider(),
    )

    assert first.document_date == "2026-01-15"
    assert second.document_date == first.document_date
