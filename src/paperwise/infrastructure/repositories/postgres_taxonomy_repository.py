from sqlalchemy import func, select

from paperwise.application.services.taxonomy import normalize_name, to_title_case
from paperwise.application.services.taxonomy_stats import tag_stats_from_metadata
from paperwise.infrastructure.repositories.postgres_models import (
    CorrespondentRow,
    DocumentRow,
    DocumentTypeRow,
    LLMParseResultRow,
    TagRow,
)


def _ordered_count_rows(rows: list[tuple[str, int]]) -> list[tuple[str, int]]:
    return sorted(rows, key=lambda item: (-item[1], item[0].casefold()))


class PostgresTaxonomyRepositoryMixin:
    def list_correspondents(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(CorrespondentRow).order_by(CorrespondentRow.name)).all()
            return [row.name for row in rows]

    def list_document_types(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(DocumentTypeRow).order_by(DocumentTypeRow.name)).all()
            return [row.name for row in rows]

    def list_tags(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(select(TagRow).order_by(TagRow.name)).all()
            by_norm: dict[str, str] = {}
            for row in rows:
                normalized = normalize_name(row.name)
                if not normalized:
                    continue
                by_norm[normalized] = to_title_case(row.name)
            return sorted(by_norm.values())

    def list_tag_stats(self) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(select(LLMParseResultRow)).all()
            return tag_stats_from_metadata(rows)

    def list_owner_tag_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(LLMParseResultRow)
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
            ).all()
            return tag_stats_from_metadata(rows)

    def list_owner_document_type_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            value = func.trim(LLMParseResultRow.document_type)
            normalized = func.lower(value)
            rows = session.execute(
                select(normalized, func.min(value), func.count())
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
                .where(value != "")
                .group_by(normalized)
            ).all()
            return _ordered_count_rows(
                [(to_title_case(str(display)), int(count)) for _key, display, count in rows]
            )

    def list_owner_correspondent_stats(self, owner_id: str) -> list[tuple[str, int]]:
        with self._session_factory() as session:
            value = func.trim(LLMParseResultRow.correspondent)
            normalized = func.lower(value)
            rows = session.execute(
                select(normalized, func.min(value), func.count())
                .join(DocumentRow, DocumentRow.id == LLMParseResultRow.document_id)
                .where(DocumentRow.owner_id == owner_id)
                .where(value != "")
                .group_by(normalized)
            ).all()
            return _ordered_count_rows([(str(display), int(count)) for _key, display, count in rows])

    def add_correspondent(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        with self._session_factory() as session:
            if session.get(CorrespondentRow, cleaned) is None:
                session.add(CorrespondentRow(name=cleaned))
                session.commit()

    def add_document_type(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        with self._session_factory() as session:
            if session.get(DocumentTypeRow, cleaned) is None:
                session.add(DocumentTypeRow(name=cleaned))
                session.commit()

    def add_tags(self, names: list[str]) -> None:
        cleaned_names = [to_title_case(name) for name in names if name.strip()]
        if not cleaned_names:
            return
        with self._session_factory() as session:
            existing_rows = session.scalars(select(TagRow)).all()
            existing_by_norm = {normalize_name(row.name): row.name for row in existing_rows}
            for name in cleaned_names:
                normalized = normalize_name(name)
                if not normalized or normalized in existing_by_norm:
                    continue
                session.add(TagRow(name=name))
                existing_by_norm[normalized] = name
            session.commit()
