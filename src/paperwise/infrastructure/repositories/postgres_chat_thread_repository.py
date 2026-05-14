from datetime import UTC, datetime

from sqlalchemy import select

from paperwise.application.services.chat_threads import chat_thread_document_references
from paperwise.domain.models import ChatThread, ChatThreadDocumentReference
from paperwise.infrastructure.repositories.postgres_models import ChatThreadDocumentReferenceRow, ChatThreadRow


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


def _chat_thread_reference_from_row(row: ChatThreadDocumentReferenceRow) -> ChatThreadDocumentReference:
    return ChatThreadDocumentReference(
        thread_id=row.thread_id,
        owner_id=row.owner_id,
        document_id=row.document_id,
        title=row.title,
        message_count=row.message_count,
        reference_count=row.reference_count,
        question=row.question,
        source_titles=[str(title) for title in list(row.source_titles or [])],
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
            row.document_refs_indexed_at = datetime.now(UTC)
            session.query(ChatThreadDocumentReferenceRow).filter(
                ChatThreadDocumentReferenceRow.thread_id == thread.id
            ).delete(synchronize_session=False)
            for reference in chat_thread_document_references(thread):
                session.add(
                    ChatThreadDocumentReferenceRow(
                        thread_id=reference.thread_id,
                        document_id=reference.document_id,
                        owner_id=reference.owner_id,
                        title=reference.title,
                        message_count=reference.message_count,
                        reference_count=reference.reference_count,
                        question=reference.question,
                        source_titles=reference.source_titles,
                        created_at=reference.created_at,
                        updated_at=reference.updated_at,
                    )
                )
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

    def list_document_chat_thread_references(
        self,
        owner_id: str,
        document_id: str,
        limit: int = 50,
    ) -> list[ChatThreadDocumentReference]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ChatThreadDocumentReferenceRow)
                .where(ChatThreadDocumentReferenceRow.owner_id == owner_id)
                .where(ChatThreadDocumentReferenceRow.document_id == document_id)
                .order_by(ChatThreadDocumentReferenceRow.updated_at.desc())
                .limit(max(0, limit))
            ).all()
            return [_chat_thread_reference_from_row(row) for row in rows]

    def delete_chat_thread(self, owner_id: str, thread_id: str) -> bool:
        with self._session_factory() as session:
            row = session.get(ChatThreadRow, thread_id)
            if row is None or row.owner_id != owner_id:
                return False
            session.query(ChatThreadDocumentReferenceRow).filter(
                ChatThreadDocumentReferenceRow.thread_id == thread_id
            ).delete(synchronize_session=False)
            session.delete(row)
            session.commit()
            return True
