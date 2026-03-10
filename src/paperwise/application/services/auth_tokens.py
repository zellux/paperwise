import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def create_access_token(*, user_id: str, secret: str, ttl_seconds: int) -> str:
    payload = {
        "sub": user_id,
        "exp": int(datetime.now(UTC).timestamp()) + max(ttl_seconds, 60),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_part = _b64url_encode(payload_bytes)
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_part.encode("ascii"),
        digestmod=hashlib.sha256,
    ).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def decode_access_token(token: str, secret: str) -> dict | None:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_part.encode("ascii"),
        digestmod=hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_part)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected_signature, provided_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    exp = int(payload.get("exp", 0))
    if exp <= int(datetime.now(UTC).timestamp()):
        return None
    if not payload.get("sub"):
        return None
    return payload
