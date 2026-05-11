from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.llm_runtime import summarize_llm_provider


def new_ocr_details(*, requested_provider: str, auto_switch_enabled: bool) -> dict[str, object]:
    return {
        "requested_provider": requested_provider,
        "auto_switch_enabled": auto_switch_enabled,
        "attempts": {
            "text_extraction": {"attempted": False, "succeeded": False},
            "local_tesseract": {"attempted": False, "succeeded": False},
            "llm_text": {"attempted": False, "succeeded": False},
            "llm_vision": {"attempted": False, "succeeded": False},
        },
        "final_text_source": "",
        "final_text_chars": 0,
        "final_text_bytes": 0,
    }


def mark_ocr_attempt(
    ocr_details: dict[str, object],
    attempt_key: str,
    *,
    attempted: bool = True,
    succeeded: bool | None = None,
    selected: bool | None = None,
    error: str | None = None,
    **extra: object,
) -> None:
    attempts = ocr_details.get("attempts")
    if not isinstance(attempts, dict):
        return
    attempt = attempts.get(attempt_key)
    if not isinstance(attempt, dict):
        attempt = {}
        attempts[attempt_key] = attempt
    attempt["attempted"] = attempted
    if succeeded is not None:
        attempt["succeeded"] = succeeded
    if selected is not None:
        attempt["selected"] = selected
    if error:
        attempt["error"] = error
    for key, value in extra.items():
        if value is not None:
            attempt[key] = value


def set_final_ocr_source(
    ocr_details: dict[str, object],
    *,
    source: str,
    text_preview: str,
) -> None:
    final_text = str(text_preview or "")
    ocr_details["final_text_source"] = source
    ocr_details["final_text_chars"] = len(final_text)
    ocr_details["final_text_bytes"] = len(final_text.encode("utf-8"))


def set_ocr_process_details(
    ocr_details: dict[str, object],
    *,
    llm_provider: LLMProvider | None,
    text_preview: str,
) -> None:
    attempts = ocr_details.get("attempts")
    if not isinstance(attempts, dict):
        attempts = {}

    def selected(attempt_key: str) -> bool:
        attempt = attempts.get(attempt_key)
        return isinstance(attempt, dict) and bool(attempt.get("selected"))

    location = "none"
    engine = "direct_text"
    method = str(ocr_details.get("final_text_source") or "").strip() or "direct_text"
    provider_summary = summarize_llm_provider(llm_provider)
    provider_name = provider_summary["provider"]
    model = provider_summary["model"]
    base_url = provider_summary["base_url"]

    if selected("local_tesseract"):
        location = "local"
        engine = "tesseract"
        method = "local_tesseract"
        provider_name = "tesseract"
        model = None
        base_url = None
    elif selected("llm_vision"):
        location = "remote"
        engine = "llm"
        method = "llm_vision"
    elif selected("llm_text"):
        location = "remote"
        engine = "llm"
        method = "llm_text"

    ocr_details["process"] = {
        "location": location,
        "engine": engine,
        "method": method,
        "provider": provider_name,
        "model": model,
        "base_url": base_url,
        "result_size_bytes": len(str(text_preview or "").encode("utf-8")),
    }
