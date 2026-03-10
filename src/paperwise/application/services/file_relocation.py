from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def _sanitize_filename(value: str) -> str:
    cleaned = Path(value).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        return "uploaded-document.bin"
    return cleaned


def move_blob_to_processed(
    *,
    blob_uri: str,
    object_store_root: str,
    document_id: str,
    original_filename: str,
    content_type: str,
    checksum_sha256: str,
    size_bytes: int,
) -> str:
    parsed = urlparse(blob_uri)
    if parsed.scheme != "file":
        return blob_uri

    source_path = Path(unquote(parsed.path))
    root_dir = Path(object_store_root).expanduser().resolve()
    target_filename = f"{document_id}_{_sanitize_filename(original_filename)}"
    target_path = root_dir / "processed" / document_id / target_filename
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path.exists() and source_path.resolve() != target_path.resolve():
        if target_path.exists():
            target_path.unlink()
        shutil.move(str(source_path), str(target_path))
    elif not target_path.exists():
        return blob_uri

    metadata_path = target_path.with_name(f"{target_path.name}.metadata.json")
    metadata = {
        "original_filename": original_filename,
        "content_type": content_type,
        "checksum_sha256": checksum_sha256,
        "size_bytes": size_bytes,
        "stored_key": str(target_path.relative_to(root_dir)),
        "moved_from_blob_uri": blob_uri,
        "moved_at": datetime.now(UTC).isoformat(),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    return target_path.resolve().as_uri()
