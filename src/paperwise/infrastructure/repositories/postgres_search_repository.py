from sqlalchemy import select

from paperwise.application.services.search_text import extract_search_snippet, tokenize_search_query
from paperwise.domain.models import DocumentSearchHit
from paperwise.infrastructure.repositories.postgres_document_mapper import document_from_row
from paperwise.infrastructure.repositories.postgres_models import DocumentRow, LLMParseResultRow, ParseResultRow


class PostgresSearchRepositoryMixin:
    def search_documents(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[DocumentSearchHit]:
        terms = tokenize_search_query(query)
        if not terms:
            return []
        scoped_ids = sorted(set(document_ids or []))
        has_scope = document_ids is not None
        with self._session_factory() as session:
            query_stmt = select(DocumentRow).where(DocumentRow.owner_id == owner_id)
            if has_scope:
                if not scoped_ids:
                    return []
                query_stmt = query_stmt.where(DocumentRow.id.in_(scoped_ids))
            doc_rows = session.scalars(query_stmt.order_by(DocumentRow.created_at.desc())).all()
            if not doc_rows:
                return []
            ids = [row.id for row in doc_rows]
            parse_rows = session.scalars(select(ParseResultRow).where(ParseResultRow.document_id.in_(ids))).all()
            llm_rows = session.scalars(select(LLMParseResultRow).where(LLMParseResultRow.document_id.in_(ids))).all()
            parse_by_id = {row.document_id: row for row in parse_rows}
            llm_by_id = {row.document_id: row for row in llm_rows}

            hits: list[DocumentSearchHit] = []
            for row in doc_rows:
                parse_row = parse_by_id.get(row.id)
                llm_row = llm_by_id.get(row.id)
                searchable_parts = [
                    row.filename or "",
                    parse_row.text_preview if parse_row is not None else "",
                    llm_row.suggested_title if llm_row is not None else "",
                    llm_row.correspondent if llm_row is not None else "",
                    llm_row.document_type if llm_row is not None else "",
                    " ".join(llm_row.tags or []) if llm_row is not None else "",
                ]
                searchable_text = " ".join(part for part in searchable_parts if part).strip()
                lowered = searchable_text.lower()
                matched = [term for term in terms if term in lowered]
                if not matched:
                    continue
                score = float(sum(lowered.count(term) for term in matched))
                snippet = extract_search_snippet(
                    parse_row.text_preview if parse_row is not None else searchable_text,
                    matched,
                )
                hits.append(
                    DocumentSearchHit(
                        document=document_from_row(row),
                        score=score,
                        snippet=snippet,
                        matched_terms=matched,
                    )
                )
            hits.sort(key=lambda hit: (hit.score, hit.document.created_at), reverse=True)
            return hits[: max(1, limit)]
