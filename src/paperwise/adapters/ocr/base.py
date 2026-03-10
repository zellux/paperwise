from paperwise.application.interfaces import OCRProvider


class BaseOCRAdapter(OCRProvider):
    def extract_text(self, uri: str) -> str:
        raise NotImplementedError

