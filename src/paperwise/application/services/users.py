from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from os import urandom
from uuid import uuid4

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import User

_HASH_NAME = "sha256"
_ITERATIONS = 240_000
_SALT_BYTES = 16


@dataclass(slots=True)
class CreateUserCommand:
    email: str
    full_name: str
    password: str


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _hash_password(password: str) -> str:
    salt = urandom(_SALT_BYTES)
    digest = pbkdf2_hmac(
        _HASH_NAME,
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )
    return f"pbkdf2_{_HASH_NAME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4:
        return False

    scheme, iterations_raw, salt_raw, expected_raw = parts
    if not scheme.startswith("pbkdf2_"):
        return False
    hash_name = scheme.replace("pbkdf2_", "", 1)
    if not hash_name:
        return False
    try:
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_raw)
        expected = bytes.fromhex(expected_raw)
    except ValueError:
        return False

    candidate = pbkdf2_hmac(
        hash_name,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return compare_digest(candidate, expected)


def create_user(command: CreateUserCommand, repository: DocumentRepository) -> User:
    email = _normalize_email(command.email)
    full_name = " ".join(command.full_name.split()).strip()
    password = command.password
    if not email:
        raise ValueError("Email is required")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("Email is invalid")
    if not full_name:
        raise ValueError("Full name is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if repository.get_user_by_email(email) is not None:
        raise ValueError("User with this email already exists")

    user = User(
        id=str(uuid4()),
        email=email,
        full_name=full_name,
        password_hash=_hash_password(password),
        is_active=True,
        created_at=datetime.now(UTC),
    )
    repository.save_user(user)
    return user


def authenticate_user(email: str, password: str, repository: DocumentRepository) -> User | None:
    user = repository.get_user_by_email(_normalize_email(email))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def change_user_password(
    *,
    user: User,
    current_password: str,
    new_password: str,
    repository: DocumentRepository,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters")
    if verify_password(new_password, user.password_hash):
        raise ValueError("New password must be different from current password")

    user.password_hash = _hash_password(new_password)
    repository.save_user(user)
