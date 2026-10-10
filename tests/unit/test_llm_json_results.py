import json

import httpx
import pytest

from paperwise.infrastructure.llm.json_results import LLMResponseFormatError
from paperwise.infrastructure.llm.metadata_prompt import extract_metadata_result
from paperwise.infrastructure.llm.ocr_prompt import extract_ocr_text_result
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider


@pytest.mark.parametrize("extract", [extract_metadata_result, extract_ocr_text_result])
@pytest.mark.parametrize("payload", [[], [{}, {}], ["text"], [[{}]], None, 42, "text", True])
def test_result_extractors_reject_non_object_json(extract, payload):
    with pytest.raises(LLMResponseFormatError, match="Expected an LLM JSON object"):
        extract(payload)


def test_single_object_array_preserves_metadata_and_nested_ocr_lines():
    assert extract_metadata_result([{"suggested_title": "Invoice", "tags": ["Tax"]}]) == {
        "suggested_title": "Invoice", "tags": ["Tax"],
    }
    assert extract_ocr_text_result([{"ocr_text": [{"text": "Invoice"}, "Total: 10"]}]) == "Invoice\nTotal: 10"


def _call_provider(provider, task):
    if task == "metadata":
        return provider.suggest_metadata(
            filename="invoice.pdf", text_preview="Invoice", current_correspondent=None,
            current_document_type=None, existing_correspondents=[], existing_document_types=[], existing_tags=[],
        )
    if task == "text_ocr":
        return provider.extract_ocr_text(filename="invoice.pdf", content_type="application/pdf", text_preview="Invoice")
    return provider.extract_ocr_text_from_images(filename="invoice.pdf", image_data_urls=["data:image/png;base64,YQ=="])


@pytest.mark.parametrize("task", ["metadata", "text_ocr", "image_ocr"])
@pytest.mark.parametrize("recover", [True, False])
def test_openai_retries_invalid_result_shape_and_reports_exhausted_failure(task, recover):
    calls = []

    def respond(request):
        calls.append(request)
        payload = [{"suggested_title": "Invoice", "ocr_text": "Invoice"}] if recover and len(calls) == 2 else [{}, {}]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    provider = OpenAILLMProvider(api_key="test", model="test")
    provider._client.close()
    with httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(respond)) as client:
        provider._client = client
        if recover:
            result = _call_provider(provider, task)
            assert result == ({"suggested_title": "Invoice"} if task == "metadata" else "Invoice")
        else:
            with pytest.raises(LLMResponseFormatError, match="received list"):
                _call_provider(provider, task)
    assert len(calls) == 2
