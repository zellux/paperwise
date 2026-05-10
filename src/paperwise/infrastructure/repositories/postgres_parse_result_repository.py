from paperwise.application.services.taxonomy import normalize_name, to_title_case
from paperwise.domain.models import LLMParseResult, ParseResult
from paperwise.infrastructure.repositories.postgres_models import LLMParseResultRow, ParseResultRow


def _normalize_tags(values: list[str]) -> list[str]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_name(str(value))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(to_title_case(str(value)))
    return normalized_values


def llm_parse_result_from_row(row: LLMParseResultRow) -> LLMParseResult:
    return LLMParseResult(
        document_id=row.document_id,
        suggested_title=row.suggested_title,
        document_date=row.document_date,
        correspondent=row.correspondent,
        document_type=row.document_type,
        tags=_normalize_tags(list(row.tags or [])),
        created_correspondent=row.created_correspondent,
        created_document_type=row.created_document_type,
        created_tags=_normalize_tags(list(row.created_tags or [])),
        created_at=row.created_at,
        llm_details=None,
    )


class PostgresParseResultRepositoryMixin:
    def save_parse_result(self, result: ParseResult) -> None:
        with self._session_factory() as session:
            row = session.get(ParseResultRow, result.document_id)
            if row is None:
                row = ParseResultRow(document_id=result.document_id)
                session.add(row)
            row.parser = result.parser
            row.status = result.status
            row.size_bytes = result.size_bytes
            row.page_count = result.page_count
            row.text_preview = result.text_preview
            row.created_at = result.created_at
            session.commit()

    def get_parse_result(self, document_id: str) -> ParseResult | None:
        with self._session_factory() as session:
            row = session.get(ParseResultRow, document_id)
            if row is None:
                return None
            return ParseResult(
                document_id=row.document_id,
                parser=row.parser,
                status=row.status,
                size_bytes=row.size_bytes,
                page_count=row.page_count,
                text_preview=row.text_preview,
                created_at=row.created_at,
                ocr_details=None,
            )

    def save_llm_parse_result(self, result: LLMParseResult) -> None:
        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, result.document_id)
            if row is None:
                row = LLMParseResultRow(document_id=result.document_id)
                session.add(row)
            row.suggested_title = result.suggested_title
            row.document_date = result.document_date
            row.correspondent = result.correspondent
            row.document_type = result.document_type
            row.tags = _normalize_tags(result.tags)
            row.created_correspondent = result.created_correspondent
            row.created_document_type = result.created_document_type
            row.created_tags = _normalize_tags(result.created_tags)
            row.created_at = result.created_at
            session.commit()

    def get_llm_parse_result(self, document_id: str) -> LLMParseResult | None:
        with self._session_factory() as session:
            row = session.get(LLMParseResultRow, document_id)
            if row is None:
                return None
            return llm_parse_result_from_row(row)
