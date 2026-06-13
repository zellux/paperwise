from typing import Any

OCR_SYSTEM_PROMPT = (
    "You are an OCR transcription engine. "
    "Transcribe document text faithfully from the provided extracted content. "
    "Do not summarize. Do not rewrite for style. Do not infer missing text. "
    "Preserve original casing, numbers, and key punctuation. "
    "Return strict JSON with one key: ocr_text."
)

OCR_USER_GUIDANCE = (
    "Return only recognized document text in reading order. "
    "Keep line breaks where they improve readability. "
    "If text is unclear, keep best-effort transcription without inventing content."
)


def build_ocr_user_prompt(
    *,
    filename: str,
    content_type: str,
    text_preview: str,
) -> dict[str, Any]:
    return {
        "filename": filename,
        "content_type": content_type,
        "text_preview": text_preview,
        "guidance": OCR_USER_GUIDANCE,
    }


def extract_ocr_text_result(parsed: dict[str, Any]) -> str:
    ocr_text = parsed.get("ocr_text")
    if isinstance(ocr_text, str):
        return ocr_text.strip()
    if isinstance(ocr_text, list):
        lines = [_coerce_ocr_text_part(item) for item in ocr_text]
        return "\n".join(line for line in lines if line).strip()
    if isinstance(ocr_text, dict):
        return _coerce_ocr_text_part(ocr_text)
    return ""


def _coerce_ocr_text_part(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "line", "content", "ocr_text"):
            raw = value.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        lines = [_coerce_ocr_text_part(item) for item in value.values()]
        return " ".join(line for line in lines if line).strip()
    if isinstance(value, list):
        lines = [_coerce_ocr_text_part(item) for item in value]
        return "\n".join(line for line in lines if line).strip()
    return ""
