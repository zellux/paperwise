import json

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
        existing_correspondents=["Experian"],
        existing_document_types=["Credit Report"],
        existing_tags=["credit"],
    )

    assert result == {"suggested_title": "Only Title"}
