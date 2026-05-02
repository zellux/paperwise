import json

from paperwise.infrastructure.llm.gemini_llm_provider import GeminiLLMProvider, TOOL_CHAT_SYSTEM_PROMPT
from paperwise.infrastructure.llm.grounded_qa_prompt import GROUNDED_QA_SYSTEM_PROMPT
from paperwise.infrastructure.llm.metadata_prompt import SYSTEM_PROMPT
from paperwise.infrastructure.llm.ocr_prompt import OCR_SYSTEM_PROMPT


def test_gemini_provider_parses_json_response(monkeypatch) -> None:
    captured_call: dict[str, object] = {}

    class FakeResponse:
        text = json.dumps(
            {
                "suggested_title": "Credit Report March 2026",
                "document_date": "2026-03-01",
                "correspondent": "Experian",
                "document_type": "Credit Report",
                "tags": ["credit", "identity"],
            }
        )

        class usage_metadata:
            total_token_count = 321

        def model_dump(self, *args, **kwargs) -> dict:
            del args, kwargs
            return {
                "usage_metadata": {"total_token_count": 321},
                "candidates": [{"content": {"parts": [{"text": self.text}]}}],
            }

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config: object) -> FakeResponse:
            captured_call["model"] = model
            captured_call["contents"] = contents
            captured_call["config"] = config
            return FakeResponse()

    provider = GeminiLLMProvider(api_key="k", model="gemini-test")
    monkeypatch.setattr(provider, "_client", type("FakeClient", (), {"models": FakeModels()})())

    result = provider.suggest_metadata(
        filename="credit.pdf",
        text_preview="sample",
        current_correspondent="Experian",
        current_document_type="Credit Report",
        existing_correspondents=["Experian"],
        existing_document_types=["Credit Report"],
        existing_tags=["credit"],
    )

    assert result["suggested_title"] == "Credit Report March 2026"
    assert result["document_date"] == "2026-03-01"
    assert result["correspondent"] == "Experian"
    assert result["document_type"] == "Credit Report"
    assert result["tags"] == ["credit", "identity"]
    assert result["llm_total_tokens"] == 321
    assert captured_call["model"] == "gemini-test"
    assert isinstance(captured_call["contents"], str)
    assert getattr(captured_call["config"], "system_instruction", None) == SYSTEM_PROMPT
    assert getattr(captured_call["config"], "response_mime_type", None) == "application/json"


def test_gemini_provider_uses_ocr_specific_prompt(monkeypatch) -> None:
    captured_call: dict[str, object] = {}

    class FakeResponse:
        text = json.dumps({"ocr_text": "Invoice #123\nTotal Due: $1,200.00"})

        def model_dump(self, *args, **kwargs) -> dict:
            del args, kwargs
            return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config: object) -> FakeResponse:
            captured_call["model"] = model
            captured_call["contents"] = contents
            captured_call["config"] = config
            return FakeResponse()

    provider = GeminiLLMProvider(api_key="k", model="gemini-test")
    monkeypatch.setattr(provider, "_client", type("FakeClient", (), {"models": FakeModels()})())

    result = provider.extract_ocr_text(
        filename="invoice.pdf",
        content_type="application/pdf",
        text_preview="invoice sample text",
    )

    assert result == "Invoice #123\nTotal Due: $1,200.00"
    assert captured_call["model"] == "gemini-test"
    assert getattr(captured_call["config"], "system_instruction", None) == OCR_SYSTEM_PROMPT
    assert getattr(captured_call["config"], "max_output_tokens", None) == 3000


def test_gemini_provider_image_ocr_combines_pages(monkeypatch) -> None:
    captured_calls: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def model_dump(self, *args, **kwargs) -> dict:
            del args, kwargs
            return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}

    class FakeModels:
        def generate_content(self, *, model: str, contents: list[object], config: object) -> FakeResponse:
            captured_calls.append({"model": model, "contents": contents, "config": config})
            prompt = str(contents[0])
            page_number = int(prompt.split("Page ", 1)[1].split(" of ", 1)[0])
            return FakeResponse(json.dumps({"ocr_text": f"page-{page_number}"}))

    provider = GeminiLLMProvider(api_key="k", model="gemini-test")
    fake_client = type("FakeClient", (), {"models": FakeModels()})()
    monkeypatch.setattr(provider, "_long_running_client", fake_client)

    result = provider.extract_ocr_text_from_images(
        filename="scan.pdf",
        image_data_urls=[
            "data:image/png;base64,YQ==",
            "data:image/png;base64,Yg==",
        ],
    )

    assert result == "page-1\n\npage-2"
    assert len(captured_calls) == 2
    assert getattr(captured_calls[0]["config"], "system_instruction", None) == OCR_SYSTEM_PROMPT


def test_gemini_provider_grounded_qa_uses_long_running_client(monkeypatch) -> None:
    captured_call: dict[str, object] = {}

    class FakeResponse:
        text = json.dumps(
            {
                "answer": "The policy rate changed over time.",
                "insufficient_evidence": False,
                "citations": [],
            }
        )

        class usage_metadata:
            total_token_count = 654

        def model_dump(self, *args, **kwargs) -> dict:
            del args, kwargs
            return {
                "usage_metadata": {"total_token_count": 654},
                "candidates": [{"content": {"parts": [{"text": self.text}]}}],
            }

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config: object) -> FakeResponse:
            captured_call["model"] = model
            captured_call["contents"] = contents
            captured_call["config"] = config
            return FakeResponse()

    provider = GeminiLLMProvider(api_key="k", model="gemini-test")
    monkeypatch.setattr(
        provider,
        "_long_running_client",
        type("FakeClient", (), {"models": FakeModels()})(),
    )

    result = provider.answer_grounded(
        question="What is the history of the rate?",
        contexts=[
            {
                "chunk_id": "doc:1",
                "document_id": "doc",
                "title": "Sample",
                "content": "sample context",
            }
        ],
    )

    assert result["answer"] == "The policy rate changed over time."
    assert result["llm_total_tokens"] == 654
    assert getattr(captured_call["config"], "system_instruction", None) == GROUNDED_QA_SYSTEM_PROMPT


def test_gemini_provider_returns_tool_calls(monkeypatch) -> None:
    captured_call: dict[str, object] = {}

    class FakeResponse:
        text = json.dumps(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "search_document_chunks",
                        "arguments": {"query": "invoice"},
                    }
                ],
            }
        )

        class usage_metadata:
            total_token_count = 44

        def model_dump(self, *args, **kwargs) -> dict:
            del args, kwargs
            return {
                "usage_metadata": {"total_token_count": 44},
                "candidates": [{"content": {"parts": [{"text": self.text}]}}],
            }

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config: object) -> FakeResponse:
            captured_call["model"] = model
            captured_call["contents"] = contents
            captured_call["config"] = config
            return FakeResponse()

    provider = GeminiLLMProvider(api_key="k", model="gemini-test")
    monkeypatch.setattr(
        provider,
        "_long_running_client",
        type("FakeClient", (), {"models": FakeModels()})(),
    )

    result = provider.answer_with_tools(
        messages=[{"role": "user", "content": "Find invoices"}],
        tools=[{"type": "function", "function": {"name": "search_document_chunks"}}],
    )

    assert result["tool_calls"] == [
        {
            "id": "call-1",
            "name": "search_document_chunks",
            "arguments": '{"query": "invoice"}',
        }
    ]
    assert result["llm_total_tokens"] == 44
    assert getattr(captured_call["config"], "system_instruction", None) == TOOL_CHAT_SYSTEM_PROMPT
    assert getattr(captured_call["config"], "response_mime_type", None) == "application/json"
