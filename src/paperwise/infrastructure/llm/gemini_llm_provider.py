import base64
import binascii
import json
from typing import Any, Protocol

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - exercised in environments without optional deps.
    genai = None
    genai_types = None

from paperwise.application.interfaces import LLMProvider
from paperwise.infrastructure.llm.debug_log import log_llm_exchange
from paperwise.infrastructure.llm.grounded_qa_prompt import (
    GROUNDED_QA_SYSTEM_PROMPT,
    build_grounded_qa_user_prompt,
    extract_grounded_qa_result,
)
from paperwise.infrastructure.llm.metadata_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    extract_metadata_result,
)
from paperwise.infrastructure.llm.ocr_prompt import (
    OCR_SYSTEM_PROMPT,
    build_ocr_user_prompt,
    extract_ocr_text_result,
)
from paperwise.infrastructure.llm.retrieval_query_prompt import (
    RETRIEVAL_QUERY_SYSTEM_PROMPT,
    build_retrieval_query_user_prompt,
    extract_retrieval_query_result,
)

_DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_LONG_RUNNING_TIMEOUT_SECONDS = 120.0


class _GeminiModelsClient(Protocol):
    def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
        """Run a Gemini generate_content request."""


class _GeminiClient(Protocol):
    models: _GeminiModelsClient


def _resolve_api_version(base_url: str) -> str:
    normalized = str(base_url or "").rstrip("/")
    for version in ("v1beta", "v1alpha", "v1"):
        if normalized.endswith(f"/{version}"):
            return version
    return "v1beta"


def _resolve_custom_base_url(base_url: str) -> str | None:
    normalized = str(base_url or "").rstrip("/")
    if not normalized:
        return None
    for version in ("v1beta", "v1alpha", "v1"):
        suffix = f"/{version}"
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    default_root = _DEFAULT_GEMINI_BASE_URL.rsplit("/", 1)[0]
    if normalized and normalized != default_root:
        return normalized
    return None


def _dump_sdk_payload(value: Any) -> Any:
    if value is None:
        return None
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(mode="json", exclude_none=True)
        except TypeError:
            return model_dump()
    to_json_dict = getattr(value, "to_json_dict", None)
    if callable(to_json_dict):
        return to_json_dict()
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    text = getattr(value, "text", None)
    if isinstance(text, str) and text:
        return {"text": text}
    return str(value)


def _extract_response_text(response: Any, response_payload: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    payload = response_payload if isinstance(response_payload, dict) else _dump_sdk_payload(response)
    if isinstance(payload, dict):
        candidates = payload.get("candidates", [])
        candidate = candidates[0] if candidates else {}
        content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        extracted = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
        if extracted:
            return extracted
    raise RuntimeError("Gemini response did not include any text content.")


def _extract_total_tokens(response: Any, response_payload: Any) -> int | None:
    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata is not None:
        total = getattr(usage_metadata, "total_token_count", None)
        if isinstance(total, int):
            return total

    if isinstance(response_payload, dict):
        usage = response_payload.get("usage_metadata") or response_payload.get("usageMetadata")
        if isinstance(usage, dict):
            total = usage.get("total_token_count") or usage.get("totalTokenCount")
            if isinstance(total, int):
                return total
    return None


def _decode_image_data_url(data_url: str) -> tuple[str, bytes]:
    prefix, separator, encoded = data_url.partition(",")
    if separator != "," or ";base64" not in prefix:
        raise RuntimeError("Unsupported image data URL for Gemini OCR.")
    mime_type = prefix[5:].split(";", 1)[0].strip()
    if not mime_type:
        raise RuntimeError("Missing mime type in image data URL for Gemini OCR.")
    try:
        return mime_type, base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError("Invalid base64 image data for Gemini OCR.") from exc


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model = model
        self._api_version = _resolve_api_version(base_url)
        self._client = self._build_client(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        self._long_running_client = self._build_client(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=max(timeout_seconds, _LONG_RUNNING_TIMEOUT_SECONDS),
        )

    @staticmethod
    def _build_client(*, api_key: str, base_url: str, timeout_seconds: float) -> _GeminiClient:
        if genai is None or genai_types is None:
            raise RuntimeError(
                "Gemini support requires the google-genai package. Install project dependencies first."
            )

        http_options_kwargs: dict[str, Any] = {
            "api_version": _resolve_api_version(base_url),
            "client_args": {"timeout": timeout_seconds},
        }
        custom_base_url = _resolve_custom_base_url(base_url)
        if custom_base_url:
            # The SDK primarily documents custom base URLs for Vertex, but we still pass
            # the configured root through so existing Paperwise settings keep working when possible.
            http_options_kwargs["base_url"] = custom_base_url

        http_options = genai_types.HttpOptions(**http_options_kwargs)
        return genai.Client(api_key=api_key, http_options=http_options)

    def _build_config(
        self,
        *,
        system_instruction: str,
        max_output_tokens: int | None = None,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
    ) -> Any:
        if genai_types is None:
            raise RuntimeError(
                "Gemini support requires the google-genai package. Install project dependencies first."
            )

        config_kwargs: dict[str, Any] = {
            "system_instruction": system_instruction,
            "temperature": 0,
        }
        if max_output_tokens is not None:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if response_mime_type is not None:
            config_kwargs["response_mime_type"] = response_mime_type
        if response_json_schema is not None:
            config_kwargs["response_json_schema"] = response_json_schema
        return genai_types.GenerateContentConfig(**config_kwargs)

    def _generate_content(
        self,
        *,
        contents: Any,
        log_contents: Any,
        system_instruction: str,
        max_output_tokens: int | None = None,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
        long_running: bool = False,
    ) -> tuple[Any, Any]:
        config = self._build_config(
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            response_json_schema=response_json_schema,
        )
        request_payload = {
            "model": self._model,
            "contents": log_contents,
            "config": {
                "system_instruction": system_instruction,
                "temperature": 0,
                "max_output_tokens": max_output_tokens,
                "response_mime_type": response_mime_type,
                "response_json_schema": response_json_schema,
                "api_version": self._api_version,
            },
        }
        response: Any = None
        response_payload: Any = None
        client = self._long_running_client if long_running else self._client

        try:
            response = client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
            response_payload = _dump_sdk_payload(response)
        except Exception as exc:
            log_llm_exchange(
                provider="gemini",
                endpoint="models.generate_content",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="gemini",
            endpoint="models.generate_content",
            request_payload=request_payload,
            response_payload=response_payload,
        )
        return response, response_payload

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        user_prompt = build_user_prompt(
            filename=filename,
            text_preview=text_preview,
            current_correspondent=current_correspondent,
            current_document_type=current_document_type,
            existing_correspondents=existing_correspondents,
            existing_document_types=existing_document_types,
            existing_tags=existing_tags,
        )
        contents = json.dumps(user_prompt)
        response, response_payload = self._generate_content(
            contents=contents,
            log_contents=contents,
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        )
        text = _extract_response_text(response, response_payload)
        parsed = json.loads(text.strip())

        result = extract_metadata_result(parsed)
        total_tokens = _extract_total_tokens(response, response_payload)
        if isinstance(total_tokens, int) and total_tokens > 0:
            result["llm_total_tokens"] = total_tokens
        return result

    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        user_prompt = build_ocr_user_prompt(
            filename=filename,
            content_type=content_type,
            text_preview=text_preview,
        )
        contents = json.dumps(user_prompt)
        response, response_payload = self._generate_content(
            contents=contents,
            log_contents=contents,
            system_instruction=OCR_SYSTEM_PROMPT,
            max_output_tokens=3000,
            response_mime_type="application/json",
        )
        text = _extract_response_text(response, response_payload).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text

        extracted = extract_ocr_text_result(parsed)
        return extracted or text

    def extract_ocr_text_from_images(
        self,
        *,
        filename: str,
        image_data_urls: list[str],
    ) -> str:
        if not image_data_urls:
            raise RuntimeError("No images provided for OCR.")

        extracted_pages: list[str] = []
        total_pages = len(image_data_urls)
        for index, data_url in enumerate(image_data_urls, start=1):
            mime_type, image_bytes = _decode_image_data_url(data_url)
            prompt = (
                "Perform OCR for this document and return strict JSON with key ocr_text. "
                f"Filename: {filename}. Page {index} of {total_pages}."
            )
            if genai_types is None:
                raise RuntimeError(
                    "Gemini support requires the google-genai package. Install project dependencies first."
                )
            response, response_payload = self._generate_content(
                contents=[
                    prompt,
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                log_contents=[
                    prompt,
                    {"inline_data": {"mime_type": mime_type, "data": f"***BYTES(len={len(image_bytes)})***"}},
                ],
                system_instruction=OCR_SYSTEM_PROMPT,
                max_output_tokens=3000,
                response_mime_type="application/json",
                long_running=True,
            )
            text = _extract_response_text(response, response_payload).strip()
            try:
                parsed = json.loads(text)
                extracted = extract_ocr_text_result(parsed)
            except json.JSONDecodeError:
                extracted = text
            if extracted and extracted.strip():
                extracted_pages.append(extracted.strip())

        if extracted_pages:
            return "\n\n".join(extracted_pages).strip()
        raise RuntimeError("LLM OCR failed: provider returned empty OCR text.")

    def answer_grounded(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        user_prompt = build_grounded_qa_user_prompt(question=question, contexts=contexts)
        contents = json.dumps(user_prompt)
        response, response_payload = self._generate_content(
            contents=contents,
            log_contents=contents,
            system_instruction=GROUNDED_QA_SYSTEM_PROMPT,
            response_mime_type="application/json",
            long_running=True,
        )
        text = _extract_response_text(response, response_payload).strip()
        parsed = json.loads(text)
        result = extract_grounded_qa_result(parsed)
        total_tokens = _extract_total_tokens(response, response_payload)
        if isinstance(total_tokens, int) and total_tokens > 0:
            result["llm_total_tokens"] = total_tokens
        return result

    def rewrite_retrieval_queries(
        self,
        *,
        question: str,
    ) -> dict[str, Any]:
        user_prompt = build_retrieval_query_user_prompt(question=question)
        contents = json.dumps(user_prompt)
        response, response_payload = self._generate_content(
            contents=contents,
            log_contents=contents,
            system_instruction=RETRIEVAL_QUERY_SYSTEM_PROMPT,
            response_mime_type="application/json",
        )
        text = _extract_response_text(response, response_payload)
        parsed = json.loads(text.strip())
        return extract_retrieval_query_result(parsed, fallback_question=question)
