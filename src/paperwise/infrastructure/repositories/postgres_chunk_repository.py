from sqlalchemy import select

from paperwise.application.services.search_text import tokenize_search_query
from paperwise.domain.models import DocumentChunk, DocumentChunkSearchHit
from paperwise.infrastructure.repositories.postgres_models import DocumentChunkRow


def _chunk_from_row(row: DocumentChunkRow) -> DocumentChunk:
    return DocumentChunk(
        id=row.id,
        document_id=row.document_id,
        owner_id=row.owner_id,
        chunk_index=row.chunk_index,
        content=row.content,
        token_count=row.token_count,
        created_at=row.created_at,
    )


class PostgresChunkRepositoryMixin:
    def replace_document_chunks(
        self,
        *,
        document_id: str,
        owner_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        del owner_id
        with self._session_factory() as session:
            existing = session.scalars(
                select(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
            ).all()
            for row in existing:
                session.delete(row)
            for chunk in chunks:
                session.add(
                    DocumentChunkRow(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        owner_id=chunk.owner_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        created_at=chunk.created_at,
                    )
                )
            session.commit()

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentChunkRow)
                .where(DocumentChunkRow.document_id == document_id)
                .order_by(DocumentChunkRow.chunk_index.asc())
            ).all()
            return [_chunk_from_row(row) for row in rows]

    def search_document_chunks(
        self,
        *,
        owner_id: str,
        query: str,
        limit: int = 40,
        document_ids: list[str] | None = None,
    ) -> list[DocumentChunkSearchHit]:
        terms = tokenize_search_query(query)
        if not terms:
            return []
        scoped_ids = sorted(set(document_ids or []))
        has_scope = document_ids is not None
        with self._session_factory() as session:
            stmt = select(DocumentChunkRow).where(DocumentChunkRow.owner_id == owner_id)
            if has_scope:
                if not scoped_ids:
                    return []
                stmt = stmt.where(DocumentChunkRow.document_id.in_(scoped_ids))
            rows = session.scalars(stmt.order_by(DocumentChunkRow.created_at.desc())).all()
            hits: list[DocumentChunkSearchHit] = []
            for row in rows:
                lowered = str(row.content or "").lower()
                matched = [term for term in terms if term in lowered]
                if not matched:
                    continue
                score = float(sum(lowered.count(term) for term in matched))
                hits.append(
                    DocumentChunkSearchHit(
                        chunk=_chunk_from_row(row),
                        score=score,
                        matched_terms=matched,
                    )
                )
            hits.sort(key=lambda item: (item.score, item.chunk.created_at, item.chunk.chunk_index), reverse=True)
            return hits[: max(1, limit)]
