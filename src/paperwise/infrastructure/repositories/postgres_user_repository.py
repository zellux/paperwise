from sqlalchemy import select

from paperwise.domain.models import User, UserPreference
from paperwise.infrastructure.repositories.postgres_models import UserPreferenceRow, UserRow


def _user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=row.created_at,
    )


class PostgresUserRepositoryMixin:
    def save_user(self, user: User) -> None:
        with self._session_factory() as session:
            row = session.get(UserRow, user.id)
            if row is None:
                row = UserRow(id=user.id)
                session.add(row)
            row.email = user.email.strip().lower()
            row.full_name = user.full_name
            row.password_hash = user.password_hash
            row.is_active = user.is_active
            row.created_at = user.created_at
            session.commit()

    def get_user(self, user_id: str) -> User | None:
        with self._session_factory() as session:
            row = session.get(UserRow, user_id)
            if row is None:
                return None
            return _user_from_row(row)

    def get_user_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        with self._session_factory() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == normalized))
            if row is None:
                return None
            return _user_from_row(row)

    def list_users(self, limit: int = 100) -> list[User]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(UserRow).order_by(UserRow.created_at.desc()).limit(limit)
            ).all()
            return [_user_from_row(row) for row in rows]

    def save_user_preference(self, preference: UserPreference) -> None:
        with self._session_factory() as session:
            row = session.get(UserPreferenceRow, preference.user_id)
            if row is None:
                row = UserPreferenceRow(user_id=preference.user_id)
                session.add(row)
            row.preferences = dict(preference.preferences or {})
            session.commit()

    def get_user_preference(self, user_id: str) -> UserPreference | None:
        with self._session_factory() as session:
            row = session.get(UserPreferenceRow, user_id)
            if row is None:
                return None
            return UserPreference(
                user_id=row.user_id,
                preferences=dict(row.preferences or {}),
            )
