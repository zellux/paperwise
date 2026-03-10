from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from threading import Lock
from typing import Any

from paperwise.infrastructure.config import get_settings

_LOG_LOCK = Lock()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if any(token in normalized for token in ("api_key", "authorization", "token", "secret")):
                redacted[key] = "***REDACTED***"
                continue
            redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _trim_log_if_needed(path: Path, max_bytes: int) -> None:
    if not path.exists():
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size <= max_bytes:
        return

    keep_bytes = max(1, int(max_bytes * 0.8))
    try:
        with path.open("rb") as file:
            if size > keep_bytes:
                file.seek(size - keep_bytes)
            tail = file.read()
    except OSError:
        return

    newline_idx = tail.find(b"\n")
    if newline_idx != -1:
        tail = tail[newline_idx + 1 :]

    try:
        with path.open("wb") as file:
            file.write(tail)
    except OSError:
        return


def log_llm_exchange(
    *,
    provider: str,
    endpoint: str,
    request_payload: dict[str, Any],
    response_status: int | None = None,
    response_payload: Any = None,
    error: str | None = None,
) -> None:
    settings = get_settings()
    log_path = Path(settings.llm_debug_log_path)
    max_bytes = int(settings.llm_debug_log_max_bytes)
    if max_bytes <= 0:
        return

    record = {
        "ts": datetime.now(UTC).isoformat(),
        "provider": provider,
        "endpoint": endpoint,
        "request": _redact(request_payload),
        "response_status": response_status,
        "response": _redact(response_payload),
        "error": error,
    }
    line = json.dumps(record, ensure_ascii=True, default=str) + "\n"

    with _LOG_LOCK:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as file:
                file.write(line)
            _trim_log_if_needed(log_path, max_bytes=max_bytes)
        except OSError:
            return
