from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse


def _rebase_legacy_absolute_path(path: Path, object_store_root: Path) -> Path | None:
    marker_parts = object_store_root.parts[-2:]
    if len(marker_parts) != 2:
        return None
    parts = path.parts
    for idx in range(len(parts) - 1):
        if parts[idx] == marker_parts[0] and parts[idx + 1] == marker_parts[1]:
            suffix = parts[idx + 2 :]
            if not suffix:
                return None
            return object_store_root.joinpath(*suffix)
    return None


def _find_by_suffix(relative: Path) -> Path | None:
    cwd = Path.cwd()
    local_dir = cwd / "local"
    if not local_dir.exists() or not local_dir.is_dir():
        return None
    for root_candidate in local_dir.iterdir():
        if not root_candidate.is_dir():
            continue
        candidate = root_candidate / relative
        if candidate.exists():
            return candidate
    return None


def blob_ref_to_path(blob_ref: str, object_store_root: str) -> Path | None:
    if not blob_ref:
        return None

    root_dir = Path(object_store_root).expanduser().resolve()
    parsed = urlparse(blob_ref)
    if parsed.scheme == "file":
        direct = Path(unquote(parsed.path))
        if direct.exists():
            return direct
        rebased = _rebase_legacy_absolute_path(direct, root_dir)
        if rebased is not None:
            return rebased
        return direct
    if parsed.scheme:
        return None

    raw_ref = unquote(blob_ref).strip()
    if not raw_ref:
        return None
    relative = Path(raw_ref.lstrip("/"))
    candidate = (root_dir / relative).resolve()
    try:
        candidate.relative_to(root_dir)
    except ValueError:
        return None
    if candidate.exists():
        return candidate
    suffix_match = _find_by_suffix(relative)
    if suffix_match is not None:
        return suffix_match
    return candidate


def path_to_blob_ref(path: Path, object_store_root: str) -> str:
    root_dir = Path(object_store_root).expanduser().resolve()
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(root_dir).as_posix()
    except ValueError:
        return resolved.as_uri()
