from zapis.application.interfaces import LLMProvider


class BaseLLMAdapter(LLMProvider):
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

