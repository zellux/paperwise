from paperwise.infrastructure.llm.debug_log import _redact


def test_redact_keeps_usage_token_metrics() -> None:
    payload = {
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": 1},
            "completion_tokens_details": {"reasoning_tokens": 2},
            "inputTokenCount": 15,
            "outputTokenCount": 5,
            "totalTokenCount": 20,
        }
    }

    redacted = _redact(payload)
    assert redacted["usage"]["prompt_tokens"] == 12
    assert redacted["usage"]["completion_tokens"] == 8
    assert redacted["usage"]["total_tokens"] == 20
    assert redacted["usage"]["prompt_tokens_details"]["cached_tokens"] == 1
    assert redacted["usage"]["completion_tokens_details"]["reasoning_tokens"] == 2
    assert redacted["usage"]["inputTokenCount"] == 15
    assert redacted["usage"]["outputTokenCount"] == 5
    assert redacted["usage"]["totalTokenCount"] == 20


def test_redact_masks_sensitive_tokens_and_keys() -> None:
    payload = {
        "authorization": "Bearer abc",
        "x-api-key": "secret",
        "access_token": "token-123",
        "refresh_token": "token-456",
        "token": "token-789",
        "nested": {
            "api_key": "abc",
            "client_secret": "xyz",
        },
    }

    redacted = _redact(payload)
    assert redacted["authorization"] == "***REDACTED***"
    assert redacted["x-api-key"] == "***REDACTED***"
    assert redacted["access_token"] == "***REDACTED***"
    assert redacted["refresh_token"] == "***REDACTED***"
    assert redacted["token"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"
    assert redacted["nested"]["client_secret"] == "***REDACTED***"
