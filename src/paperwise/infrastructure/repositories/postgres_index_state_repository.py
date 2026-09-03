from sqlalchemy import select

from paperwise.domain.models import DocumentIndexState, DocumentIndexStatus
from paperwise.infrastructure.repositories.postgres_models import DocumentIndexStateRow


def _index_state_from_row(row: DocumentIndexStateRow) -> DocumentIndexState:
    return DocumentIndexState(
        document_id=row.document_id,
        owner_id=row.owner_id,
        status=DocumentIndexStatus(row.status),
        index_version=row.index_version,
        source_checksum=row.source_checksum,
        chunk_count=row.chunk_count,
        updated_at=row.updated_at,
        indexed_at=row.indexed_at,
        last_error=row.last_error,
    )


class PostgresIndexStateRepositoryMixin:
    def save_document_index_state(self, state: DocumentIndexState) -> None:
        with self._session_factory() as session:
            row = session.get(DocumentIndexStateRow, state.document_id)
            if row is None:
                row = DocumentIndexStateRow(document_id=state.document_id)
                session.add(row)
            row.owner_id = state.owner_id
            row.status = state.status.value
            row.index_version = state.index_version
            row.source_checksum = state.source_checksum
            row.chunk_count = state.chunk_count
            row.updated_at = state.updated_at
            row.indexed_at = state.indexed_at
            row.last_error = state.last_error
            session.commit()

    def get_document_index_state(self, document_id: str) -> DocumentIndexState | None:
        with self._session_factory() as session:
            row = session.get(DocumentIndexStateRow, document_id)
            return _index_state_from_row(row) if row is not None else None

    def list_document_index_states(
        self,
        *,
        owner_id: str,
        document_ids: list[str] | None = None,
    ) -> list[DocumentIndexState]:
        scoped_ids = sorted(set(document_ids or []))
        if document_ids is not None and not scoped_ids:
            return []
        with self._session_factory() as session:
            statement = select(DocumentIndexStateRow).where(DocumentIndexStateRow.owner_id == owner_id)
            if document_ids is not None:
                statement = statement.where(DocumentIndexStateRow.document_id.in_(scoped_ids))
            rows = session.scalars(statement.order_by(DocumentIndexStateRow.updated_at.desc())).all()
            return [_index_state_from_row(row) for row in rows]

    def delete_document_index_state(self, document_id: str) -> None:
        with self._session_factory() as session:
            row = session.get(DocumentIndexStateRow, document_id)
            if row is not None:
                session.delete(row)
                session.commit()
