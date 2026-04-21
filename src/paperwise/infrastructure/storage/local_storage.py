from pathlib import Path

from paperwise.application.interfaces import StorageProvider
from paperwise.application.services.storage_paths import blob_ref_to_path, path_to_blob_ref


class LocalStorageAdapter(StorageProvider):
    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path_to_blob_ref(path, str(self._root))

    def delete(self, uri: str) -> None:
        path = blob_ref_to_path(uri, str(self._root))
        if path is None or not path.exists() or not path.is_file():
            return
        path.unlink()
