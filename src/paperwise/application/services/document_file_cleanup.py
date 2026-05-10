from pathlib import Path

from paperwise.application.services.storage_paths import blob_ref_to_path


def resolve_blob_path_from_uri(blob_uri: str, object_store_root: str) -> Path | None:
    return blob_ref_to_path(blob_uri, object_store_root)


def resolve_file_path_from_uri(blob_uri: str, object_store_root: str) -> Path | None:
    resolved = resolve_blob_path_from_uri(blob_uri, object_store_root)
    if resolved is None:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    return resolved


def metadata_paths_for_blob_path(blob_path: Path) -> list[Path]:
    token_prefix = blob_path.name.split("_", 1)[0].strip()
    candidates = [
        blob_path.with_name(f"{token_prefix}.metadata.json") if token_prefix else blob_path,
        blob_path.with_name(f"{blob_path.stem}.metadata.json"),
        blob_path.with_name(f"{blob_path.name}.metadata.json"),
    ]
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_paths.append(candidate)
    return unique_paths


def delete_local_path_if_present(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def cleanup_empty_storage_dirs(start: Path, object_store_root: str) -> None:
    root_dir = Path(object_store_root).expanduser().resolve()
    current = start.resolve()
    while current != root_dir and root_dir in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
