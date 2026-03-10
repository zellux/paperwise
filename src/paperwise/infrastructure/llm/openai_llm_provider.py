import json
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider
from paperwise.infrastructure.llm.debug_log import log_llm_exchange
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


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

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
        request_payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
        }
        response: httpx.Response | None = None
        response_payload: Any = None

        try:
            response = self._client.post("/chat/completions", json=request_payload)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {"raw_text": getattr(response, "text", "")}
        except Exception as exc:
            log_llm_exchange(
                provider="openai",
                endpoint="/chat/completions",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="openai",
            endpoint="/chat/completions",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        usage = payload.get("usage", {})

        result = extract_metadata_result(parsed)

        total_tokens = usage.get("total_tokens")
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
        preview = text_preview
        response: httpx.Response | None = None
        response_payload: Any = None
        request_payload: dict[str, Any]
        last_error: Exception | None = None

        for attempt in range(2):
            user_prompt = build_ocr_user_prompt(
                filename=filename,
                content_type=content_type,
                text_preview=preview,
            )
            request_payload = {
                "model": self._model,
                "temperature": 0,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            }
            try:
                response = self._client.post("/chat/completions", json=request_payload)
                try:
                    response_payload = response.json()
                except ValueError:
                    response_payload = {"raw_text": getattr(response, "text", "")}
                break
            except Exception as exc:
                last_error = exc
                log_llm_exchange(
                    provider="openai",
                    endpoint="/chat/completions",
                    request_payload=request_payload,
                    error=str(exc),
                )
                if isinstance(exc, httpx.ReadTimeout) and attempt == 0 and len(preview) > 2000:
                    # Retry once with a smaller preview to reduce OCR latency.
                    preview = preview[: min(3000, len(preview) // 2)]
                    continue
                raise

        if response is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("OCR request failed without a response.")

        log_llm_exchange(
            provider="openai",
            endpoint="/chat/completions",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        content = str(payload["choices"][0]["message"]["content"]).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content

        extracted = extract_ocr_text_result(parsed)
        return extracted or content

    def extract_ocr_text_from_images(
        self,
        *,
        filename: str,
        image_data_urls: list[str],
    ) -> str:
        if not image_data_urls:
            raise RuntimeError("No images provided for OCR.")
        extracted_pages: list[str] = []
        last_error: Exception | None = None

        for index, image_url in enumerate(image_data_urls, start=1):
            request_payload = {
                "model": self._model,
                "temperature": 0,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Perform OCR for this document and return strict JSON "
                                    "with key ocr_text. Filename: "
                                    + filename
                                    + f". Page {index} of {len(image_data_urls)}."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    },
                ],
            }
            response: httpx.Response | None = None
            response_payload: Any = None

            for attempt in range(2):
                try:
                    # Dense scanned pages can take much longer than metadata calls.
                    try:
                        response = self._client.post(
                            "/chat/completions",
                            json=request_payload,
                            timeout=120.0,
                        )
                    except TypeError:
                        # Test doubles may not accept per-request timeout kwargs.
                        response = self._client.post("/chat/completions", json=request_payload)
                    try:
                        response_payload = response.json()
                    except ValueError:
                        response_payload = {"raw_text": getattr(response, "text", "")}
                    break
                except Exception as exc:
                    last_error = exc
                    log_llm_exchange(
                        provider="openai",
                        endpoint="/chat/completions",
                        request_payload=request_payload,
                        error=str(exc),
                    )
                    if isinstance(exc, httpx.ReadTimeout) and attempt == 0:
                        continue
                    break

            if response is None:
                continue

            log_llm_exchange(
                provider="openai",
                endpoint="/chat/completions",
                request_payload=request_payload,
                response_status=getattr(response, "status_code", None),
                response_payload=response_payload,
            )
            response.raise_for_status()
            payload = response_payload if isinstance(response_payload, dict) else response.json()
            content = str(payload["choices"][0]["message"]["content"]).strip()
            try:
                parsed = json.loads(content)
                extracted = extract_ocr_text_result(parsed)
            except json.JSONDecodeError:
                extracted = content
            if extracted and extracted.strip():
                extracted_pages.append(extracted.strip())

        if extracted_pages:
            return "\n\n".join(extracted_pages).strip()
        if last_error is not None:
            raise last_error
        raise RuntimeError("LLM OCR failed: provider returned empty OCR text.")
