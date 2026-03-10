from datetime import UTC, datetime

from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.domain.models import Document, DocumentStatus, ParseResult
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)


class FullMetadataLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
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
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
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
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        # Provider included the key, but did not infer a value.
        return {
            "document_date": None,
        }


class AcronymCaseLLMProvider:
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        return {
            "suggested_title": "Pediatric Visit",
            "document_date": "2026-03-10",
            "correspondent": "Ppmg Pediatrics",
            "document_type": "Office Visit",
            "tags": ["Ppmg", "checkup"],
        }


class TokenUsageLLMProvider:
    def __init__(self, total_tokens: int) -> None:
        self._total_tokens = total_tokens

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        return {
            "suggested_title": "Tokenized Statement",
            "document_date": "2026-03-10",
            "correspondent": "Experian",
            "document_type": "Credit Report",
            "tags": ["Credit"],
            "llm_total_tokens": self._total_tokens,
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


def test_parse_with_llm_preserves_acronym_like_casing() -> None:
    repository = InMemoryDocumentRepository()
    document = _build_document()
    parse_result = _build_parse_result(document.id)

    result = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=AcronymCaseLLMProvider(),
    )

    assert result.correspondent == "PPMG Pediatrics"
    assert "PPMG" in result.tags


def test_parse_with_llm_tracks_total_tokens_in_user_preferences() -> None:
    repository = InMemoryDocumentRepository()
    document = _build_document()
    parse_result = _build_parse_result(document.id)

    first = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=TokenUsageLLMProvider(120),
    )
    second = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=TokenUsageLLMProvider(80),
    )

    assert first.llm_total_tokens == 120
    assert second.llm_total_tokens == 80
    preference = repository.get_user_preference(document.owner_id)
    assert preference is not None
    assert preference.preferences["llm_total_tokens_processed"] == 200
