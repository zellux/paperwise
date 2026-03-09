from zapis.application.interfaces import StorageProvider


class BaseStorageAdapter(StorageProvider):
    def put(self, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError

