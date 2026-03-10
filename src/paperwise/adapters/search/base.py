from paperwise.application.interfaces import SearchProvider


class BaseSearchAdapter(SearchProvider):
    def search(self, query: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError

