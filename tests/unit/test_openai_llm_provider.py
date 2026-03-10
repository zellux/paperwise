import json

from paperwise.infrastructure.llm.ocr_prompt import OCR_SYSTEM_PROMPT
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider


def test_openai_provider_parses_json_response(monkeypatch) -> None:
    class FakeClient:
        def post(self, _path: str, json: dict):
            del json

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {
                        "usage": {"total_tokens": 321},
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        {
                                            "suggested_title": "Credit Report March 2026",
                                            "document_date": "2026-03-01",
                                            "correspondent": "Experian",
                                            "document_type": "Credit Report",
                                            "tags": ["credit", "identity"],
                                        }
                                    )
                                }
                            }
                        ]
                    }

            return Response()

    json_module = json
    provider = OpenAILLMProvider(api_key="k", model="m")
    monkeypatch.setattr(provider, "_client", FakeClient())

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


def test_openai_provider_omits_missing_keys(monkeypatch) -> None:
    class FakeClient:
        def post(self, _path: str, json: dict):
            del json

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        {
                                            "suggested_title": "Only Title",
                                        }
                                    )
                                }
                            }
                        ]
                    }

            return Response()

    json_module = json
    provider = OpenAILLMProvider(api_key="k", model="m")
    monkeypatch.setattr(provider, "_client", FakeClient())

    result = provider.suggest_metadata(
        filename="credit.pdf",
        text_preview="sample",
        current_correspondent=None,
        current_document_type=None,
        existing_correspondents=["Experian"],
        existing_document_types=["Credit Report"],
        existing_tags=["credit"],
    )

    assert result == {"suggested_title": "Only Title"}


def test_openai_provider_uses_ocr_specific_prompt(monkeypatch) -> None:
    captured_request: dict[str, dict] = {}

    class FakeClient:
        def post(self, _path: str, json: dict):
            captured_request["payload"] = json

            class Response:
                status_code = 200
                text = ""

                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        {"ocr_text": "Invoice #123\nTotal Due: $1,200.00"}
                                    )
                                }
                            }
                        ]
                    }

            return Response()

    json_module = json
    provider = OpenAILLMProvider(api_key="k", model="m")
    monkeypatch.setattr(provider, "_client", FakeClient())

    result = provider.extract_ocr_text(
        filename="invoice.pdf",
        content_type="application/pdf",
        text_preview="invoice sample text",
    )

    assert result == "Invoice #123\nTotal Due: $1,200.00"
    assert captured_request["payload"]["messages"][0]["content"] == OCR_SYSTEM_PROMPT


def test_openai_provider_uses_image_ocr_payload(monkeypatch) -> None:
    captured_request: dict[str, dict] = {}

    class FakeClient:
        def post(self, _path: str, json: dict):
            captured_request["payload"] = json

            class Response:
                status_code = 200
                text = ""

                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        {"ocr_text": "Detected page text from image"}
                                    )
                                }
                            }
                        ]
                    }

            return Response()

    json_module = json
    provider = OpenAILLMProvider(api_key="k", model="m")
    monkeypatch.setattr(provider, "_client", FakeClient())

    result = provider.extract_ocr_text_from_images(
        filename="scan.pdf",
        image_data_urls=["data:image/png;base64,abc123"],
    )

    assert result == "Detected page text from image"
    user_content = captured_request["payload"]["messages"][1]["content"]
    assert isinstance(user_content, list)
    assert any(item.get("type") == "image_url" for item in user_content if isinstance(item, dict))


def test_openai_provider_image_ocr_calls_each_page_and_combines(monkeypatch) -> None:
    captured_requests: list[dict] = []

    class FakeClient:
        def post(self, _path: str, json: dict):
            captured_requests.append(json)
            call_index = len(captured_requests)

            class Response:
                status_code = 200
                text = ""

                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        {"ocr_text": f"page-{call_index}"}
                                    )
                                }
                            }
                        ]
                    }

            return Response()

    json_module = json
    provider = OpenAILLMProvider(api_key="k", model="m")
    monkeypatch.setattr(provider, "_client", FakeClient())

    result = provider.extract_ocr_text_from_images(
        filename="scan.pdf",
        image_data_urls=["data:image/png;base64,a", "data:image/png;base64,b"],
    )

    assert result == "page-1\n\npage-2"
    assert len(captured_requests) == 2
