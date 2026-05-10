from sqlalchemy import select

from paperwise.domain.models import ChatThread
from paperwise.infrastructure.repositories.postgres_models import ChatThreadRow


def _chat_thread_from_row(row: ChatThreadRow) -> ChatThread:
    return ChatThread(
        id=row.id,
        owner_id=row.owner_id,
        title=row.title,
        messages=[dict(message) for message in list(row.messages or []) if isinstance(message, dict)],
        token_usage=dict(row.token_usage or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresChatThreadRepositoryMixin:
    def save_chat_thread(self, thread: ChatThread) -> None:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread.id)
            if row is None:
                row = ChatThreadRow(id=thread.id)
                session.add(row)
            row.owner_id = thread.owner_id
            row.title = thread.title
            row.messages = [dict(message) for message in thread.messages]
            row.token_usage = dict(thread.token_usage or {})
            row.created_at = thread.created_at
            row.updated_at = thread.updated_at
            session.commit()

    def get_chat_thread(self, owner_id: str, thread_id: str) -> ChatThread | None:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread_id)
            if row is None or row.owner_id != owner_id:
                return None
            return _chat_thread_from_row(row)

    def list_chat_threads(self, owner_id: str, limit: int = 20) -> list[ChatThread]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ChatThreadRow)
                .where(ChatThreadRow.owner_id == owner_id)
                .order_by(ChatThreadRow.updated_at.desc())
                .limit(max(0, limit))
            ).all()
            return [_chat_thread_from_row(row) for row in rows]

    def delete_chat_thread(self, owner_id: str, thread_id: str) -> bool:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread_id)
            if row is None or row.owner_id != owner_id:
                return False
            session.delete(row)
            session.commit()
            return True
