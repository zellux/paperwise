from sqlalchemy import select

from paperwise.domain.models import DocumentHistoryEvent, HistoryActorType, HistoryEventType
from paperwise.infrastructure.repositories.postgres_models import DocumentHistoryEventRow


def _history_event_from_row(row: DocumentHistoryEventRow) -> DocumentHistoryEvent:
    return DocumentHistoryEvent(
        id=row.id,
        document_id=row.document_id,
        event_type=HistoryEventType(row.event_type),
        actor_type=HistoryActorType(row.actor_type),
        actor_id=row.actor_id,
        source=row.source,
        changes=dict(row.changes or {}),
        created_at=row.created_at,
    )


class PostgresHistoryRepositoryMixin:
    def append_history_events(self, events: list[DocumentHistoryEvent]) -> None:
        if not events:
            return
        with self._session_factory() as session:
            for event in events:
                session.add(
                    DocumentHistoryEventRow(
                        id=event.id,
                        document_id=event.document_id,
                        event_type=event.event_type.value,
                        actor_type=event.actor_type.value,
                        actor_id=event.actor_id,
                        source=event.source,
                        changes=event.changes,
                        created_at=event.created_at,
                    )
                )
            session.commit()

    def list_history(
        self,
        document_id: str,
        *,
        limit: int = 100,
    ) -> list[DocumentHistoryEvent]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(DocumentHistoryEventRow)
                .where(DocumentHistoryEventRow.document_id == document_id)
                .order_by(DocumentHistoryEventRow.created_at.desc())
                .limit(limit)
            ).all()
            return [_history_event_from_row(row) for row in rows]
