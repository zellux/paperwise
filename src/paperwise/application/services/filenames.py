from __future__ import annotations

import re
from pathlib import Path


MAX_FILENAME_COMPONENT_BYTES = 255
DEFAULT_UPLOAD_FILENAME = "uploaded-document.bin"


def sanitize_storage_filename(
    value: str,
    *,
    reserved_prefix: str = "",
    reserved_suffix: str = "",
) -> str:
    cleaned = Path(value).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        cleaned = DEFAULT_UPLOAD_FILENAME

    max_bytes = (
        MAX_FILENAME_COMPONENT_BYTES
        - len(reserved_prefix.encode("utf-8"))
        - len(reserved_suffix.encode("utf-8"))
    )
    if max_bytes <= 0:
        return DEFAULT_UPLOAD_FILENAME[:MAX_FILENAME_COMPONENT_BYTES]
    if len(cleaned.encode("utf-8")) <= max_bytes:
        return cleaned

    suffix = Path(cleaned).suffix
    if suffix and len(suffix.encode("utf-8")) >= max_bytes:
        suffix = ""
    stem = cleaned[: -len(suffix)] if suffix else cleaned
    max_stem_bytes = max_bytes - len(suffix.encode("utf-8"))
    truncated_stem = stem.encode("utf-8")[:max_stem_bytes].decode("utf-8", "ignore").rstrip("._-")
    if not truncated_stem:
        truncated_stem = DEFAULT_UPLOAD_FILENAME.rsplit(".", 1)[0][:max_stem_bytes]
    return f"{truncated_stem}{suffix}"
