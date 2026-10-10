import json

import httpx
import pytest

from paperwise.application.services import llm_provider_factory
from paperwise.application.services.llm_provider_factory import resolve_llm_provider_from_preferences
from paperwise.domain.models import UserPreference
from paperwise.infrastructure.config import Settings
from paperwise.infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.server.http_llm_provider import resolve_http_llm_provider_for_user
from paperwise.workers.tasks import _resolve_metadata_llm_provider_for_owner, _resolve_ocr_llm_provider_for_owner


@pytest.mark.parametrize("timeout", [None, 7.5, 300.0])
@pytest.mark.parametrize("task", ["metadata", "text_ocr", "image_ocr", "grounded_qa", "rewrite", "tools", "stream"])
def test_openai_request_timeouts_cover_all_model_operations(timeout, task):
    captured = []

    def respond(request):
        captured.append(request.extensions["timeout"])
        if json.loads(request.content).get("stream"):
            chunk = {"choices": [{"delta": {"content": "Answer"}, "finish_reason": "stop"}]}
            return httpx.Response(200, text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n")
        content = json.dumps({"suggested_title": "Invoice", "ocr_text": "Invoice", "answer": "Answer", "queries": ["Invoice"]})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    provider = OpenAILLMProvider(api_key="test", model="test", timeout_seconds=timeout)
    client_timeout = provider._client.timeout
    provider._client.close()
    with httpx.Client(base_url="https://example.test", timeout=client_timeout, transport=httpx.MockTransport(respond)) as client:
        provider._client = client
        if task == "metadata":
            provider.suggest_metadata(
                filename="invoice.pdf", text_preview="Invoice", current_correspondent=None,
                current_document_type=None, existing_correspondents=[], existing_document_types=[], existing_tags=[],
            )
        elif task == "text_ocr":
            provider.extract_ocr_text(filename="invoice.pdf", content_type="application/pdf", text_preview="Invoice")
        elif task == "image_ocr":
            provider.extract_ocr_text_from_images(filename="invoice.pdf", image_data_urls=["data:image/png;base64,YQ=="])
        elif task == "grounded_qa":
            provider.answer_grounded(question="Invoice?", contexts=[])
        elif task == "rewrite":
            provider.rewrite_retrieval_queries(question="Invoice?")
        elif task == "tools":
            provider.answer_with_tools(messages=[], tools=[])
        else:
            list(provider.iter_answer_with_tools(messages=[], tools=[]))
    expected = timeout if timeout is not None else (30.0 if task in {"text_ocr", "rewrite"} else 120.0)
    assert captured == [{"connect": expected, "read": expected, "write": expected, "pool": expected}]


@pytest.mark.parametrize("timeout", [None, 7.5, 300.0])
def test_gemini_ordinary_and_long_clients_respect_explicit_timeout(monkeypatch, timeout):
    captured = []

    def build_client(**kwargs):
        captured.append(kwargs["timeout_seconds"])
        return object()

    monkeypatch.setattr(GeminiLLMProvider, "_build_client", staticmethod(build_client))
    GeminiLLMProvider(api_key="test", model="test", timeout_seconds=timeout)
    assert captured == ([30.0, 120.0] if timeout is None else [timeout, timeout])


def _preferences(provider):
    return {
        "llm_connections": [{"id": "primary", "name": "Primary", "provider": provider,
                             "api_key": "sk-test" if provider == "openai" else "test-key",
                             "base_url": "https://example.test/v1" if provider == "custom" else "", "default_model": "test"}],
        "llm_routing": {"metadata": {"connection_id": "primary"}, "grounded_qa": {"connection_id": "primary"},
                        "ocr": {"engine": "llm", "connection_id": "primary"}},
    }


@pytest.mark.parametrize("provider_name", ["openai", "gemini", "custom"])
@pytest.mark.parametrize("task", ["metadata", "grounded_qa", "ocr"])
def test_factory_applies_deployment_timeout_to_each_provider_and_task(monkeypatch, provider_name, task):
    monkeypatch.setattr(llm_provider_factory, "get_settings", lambda: Settings(_env_file=None, llm_request_timeout_seconds=7.5))
    monkeypatch.setattr(llm_provider_factory, "OpenAILLMProvider", lambda **kwargs: kwargs)
    monkeypatch.setattr(llm_provider_factory, "GeminiLLMProvider", lambda **kwargs: kwargs)
    result = resolve_llm_provider_from_preferences(preferences=_preferences(provider_name), task=task)
    assert result["timeout_seconds"] == 7.5


def test_http_and_worker_use_the_same_deployment_timeout(monkeypatch):
    monkeypatch.setattr(llm_provider_factory, "get_settings", lambda: Settings(_env_file=None, llm_request_timeout_seconds=300))
    monkeypatch.setattr(llm_provider_factory, "OpenAILLMProvider", lambda **kwargs: kwargs)
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(UserPreference(user_id="owner", preferences=_preferences("custom")))
    http = resolve_http_llm_provider_for_user(repository=repository, user_id="owner")
    worker = _resolve_metadata_llm_provider_for_owner(repository, "owner", None)
    ocr = _resolve_ocr_llm_provider_for_owner(repository, "owner", None, "llm_separate")
    assert [provider["timeout_seconds"] for provider in (http, worker, ocr)] == [300, 300, 300]
