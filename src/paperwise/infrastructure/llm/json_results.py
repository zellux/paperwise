from typing import Any


class LLMResponseFormatError(ValueError):
    """The model returned JSON that does not satisfy the result contract."""


def require_result_object(parsed: Any) -> dict[str, Any]:
    # Some compatible providers wrap their object despite json_object mode.
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise LLMResponseFormatError(
            "Expected an LLM JSON object or a single-element array containing an object; "
            f"received {type(parsed).__name__}."
        )
    return parsed
