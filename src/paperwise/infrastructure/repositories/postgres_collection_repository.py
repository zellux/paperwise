from datetime import UTC, datetime

from sqlalchemy import select

from paperwise.domain.models import Collection
from paperwise.infrastructure.repositories.postgres_models import CollectionDocumentRow, CollectionRow


def _collection_from_row(row: CollectionRow) -> Collection:
    return Collection(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresCollectionRepositoryMixin:
    def create_collection(self, collection: Collection) -> None:
        with self._session_factory() as session:
            row = session.get(CollectionRow, collection.id)
            if row is None:
                row = CollectionRow(id=collection.id)
                session.add(row)
            row.owner_id = collection.owner_id
            row.name = collection.name
            row.description = collection.description
            row.created_at = collection.created_at
            row.updated_at = collection.updated_at
            session.commit()

    def get_collection(self, collection_id: str) -> Collection | None:
        with self._session_factory() as session:
            row = session.get(CollectionRow, collection_id)
            if row is None:
                return None
            return _collection_from_row(row)

    def list_collections(self, owner_id: str) -> list[Collection]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(CollectionRow)
                .where(CollectionRow.owner_id == owner_id)
                .order_by(CollectionRow.updated_at.desc())
            ).all()
            return [_collection_from_row(row) for row in rows]

    def delete_collection(self, collection_id: str) -> None:
        with self._session_factory() as session:
            doc_rows = session.scalars(
                select(CollectionDocumentRow).where(CollectionDocumentRow.collection_id == collection_id)
            ).all()
            for row in doc_rows:
                session.delete(row)
            row = session.get(CollectionRow, collection_id)
            if row is not None:
                session.delete(row)
            session.commit()

    def add_collection_documents(
        self,
        collection_id: str,
        document_ids: list[str],
        *,
        added_at: datetime,
    ) -> None:
        unique_ids = sorted(set(document_ids))
        with self._session_factory() as session:
            existing = session.scalars(
                select(CollectionDocumentRow).where(CollectionDocumentRow.collection_id == collection_id)
            ).all()
            existing_ids = {row.document_id for row in existing}
            for document_id in unique_ids:
                if document_id in existing_ids:
                    continue
                session.add(
                    CollectionDocumentRow(
                        collection_id=collection_id,
                        document_id=document_id,
                        added_at=added_at,
                    )
                )
            row = session.get(CollectionRow, collection_id)
            if row is not None:
                row.updated_at = datetime.now(UTC)
            session.commit()

    def remove_collection_document(self, collection_id: str, document_id: str) -> None:
        with self._session_factory() as session:
            row = session.get(CollectionDocumentRow, {"collection_id": collection_id, "document_id": document_id})
            if row is not None:
                session.delete(row)
            collection = session.get(CollectionRow, collection_id)
            if collection is not None:
                collection.updated_at = datetime.now(UTC)
            session.commit()

    def list_collection_document_ids(self, collection_id: str) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(CollectionDocumentRow)
                .where(CollectionDocumentRow.collection_id == collection_id)
                .order_by(CollectionDocumentRow.document_id.asc())
            ).all()
            return [row.document_id for row in rows]
