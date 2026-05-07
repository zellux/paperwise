from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from paperwise.application.services.filenames import sanitize_storage_filename
from paperwise.application.services.storage_paths import blob_ref_to_path, path_to_blob_ref


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
    root_dir = Path(object_store_root).expanduser().resolve()
    source_path = blob_ref_to_path(blob_uri, object_store_root)
    if source_path is None:
        return blob_uri
    target_basename = sanitize_storage_filename(
        original_filename,
        reserved_prefix=f"{document_id}_",
        reserved_suffix=".metadata.json",
    )
    target_filename = f"{document_id}_{target_basename}"
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

    return path_to_blob_ref(target_path, object_store_root)
