from datetime import UTC, datetime

from paperwise.domain.models import Document, DocumentStatus, ParseResult, UserPreference
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.application.services.ocr_preferences import (
    resolve_owner_ocr_auto_switch,
    resolve_owner_ocr_provider,
)
from paperwise.workers import tasks as worker_tasks


def test_resolve_ocr_provider_defaults_to_llm_without_preferences() -> None:
    repository = InMemoryDocumentRepository()
    assert resolve_owner_ocr_provider(repository, "user-1") == "llm"


def test_resolve_ocr_provider_reads_saved_preference() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_provider": "tesseract"})
    )
    assert resolve_owner_ocr_provider(repository, "user-1") == "tesseract"


def test_resolve_ocr_provider_supports_separate_llm_mode() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_provider": "llm_separate"})
    )
    assert resolve_owner_ocr_provider(repository, "user-1") == "llm_separate"


def test_resolve_ocr_provider_falls_back_to_llm_for_invalid_value() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_provider": "unknown-provider"})
    )
    assert resolve_owner_ocr_provider(repository, "user-1") == "llm"


def test_resolve_ocr_auto_switch_defaults_to_false() -> None:
    repository = InMemoryDocumentRepository()
    assert resolve_owner_ocr_auto_switch(repository, "user-1") is False


def test_resolve_ocr_auto_switch_reads_saved_preference() -> None:
    repository = InMemoryDocumentRepository()
    repository.save_user_preference(
        UserPreference(user_id="user-1", preferences={"ocr_auto_switch": True})
    )
    assert resolve_owner_ocr_auto_switch(repository, "user-1") is True


def test_parse_document_task_uses_current_document_blob_uri(monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    document = Document(
        id="doc-1",
        filename="image.jpg",
        owner_id="user-1",
        blob_uri="processed/doc-1/doc-1_image.jpg",
        checksum_sha256="abc123",
        content_type="image/jpeg",
        size_bytes=123,
        status=DocumentStatus.PROCESSING,
        created_at=datetime.now(UTC),
    )
    repository.save(document)

    captured: dict[str, str] = {}

    def fake_parse_document_blob(**kwargs):
        captured["blob_uri"] = kwargs["blob_uri"]
        return ParseResult(
            document_id="doc-1",
            parser="stub-llm-ocr-separate",
            status="parsed",
            size_bytes=123,
            page_count=1,
            text_preview="sample text",
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(worker_tasks, "_build_repository", lambda: repository)
    monkeypatch.setattr(worker_tasks, "_build_llm_provider", lambda: object())
    monkeypatch.setattr(worker_tasks, "resolve_owner_ocr_provider", lambda *args, **kwargs: "llm")
    monkeypatch.setattr(worker_tasks, "resolve_owner_ocr_auto_switch", lambda *args, **kwargs: False)
    monkeypatch.setattr(worker_tasks, "_resolve_metadata_llm_provider_for_owner", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_tasks, "_resolve_ocr_llm_provider_for_owner", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_tasks, "parse_document_blob", fake_parse_document_blob)
    monkeypatch.setattr(worker_tasks, "index_document_chunks", lambda **kwargs: 1)
    monkeypatch.setattr(worker_tasks, "parse_with_llm", lambda **kwargs: None)
    monkeypatch.setattr(
        worker_tasks,
        "move_blob_to_processed",
        lambda **kwargs: "processed/doc-1/doc-1_image.jpg",
    )

    result = worker_tasks.parse_document_task(
        document_id="doc-1",
        blob_uri="incoming/doc-1_image.jpg",
        filename="image.jpg",
        content_type="image/jpeg",
    )

    updated = repository.get("doc-1")
    assert updated is not None
    assert captured["blob_uri"] == "processed/doc-1/doc-1_image.jpg"
    assert updated.status == DocumentStatus.READY
    assert result["status"] == "ready"


def test_parse_document_task_marks_document_failed_and_records_history(monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    document = Document(
        id="doc-fail",
        filename="scan.pdf",
        owner_id="user-1",
        blob_uri="incoming/scan.pdf",
        checksum_sha256="abc123",
        content_type="application/pdf",
        size_bytes=123,
        status=DocumentStatus.PROCESSING,
        created_at=datetime.now(UTC),
    )
    repository.save(document)

    def fail_parse_document_blob(**kwargs):
        del kwargs
        raise RuntimeError("LLM OCR failed: HTTP 404 from OpenRouter")

    monkeypatch.setattr(worker_tasks, "_build_repository", lambda: repository)
    monkeypatch.setattr(worker_tasks, "_build_llm_provider", lambda: object())
    monkeypatch.setattr(worker_tasks, "resolve_owner_ocr_provider", lambda *args, **kwargs: "llm")
    monkeypatch.setattr(worker_tasks, "resolve_owner_ocr_auto_switch", lambda *args, **kwargs: False)
    monkeypatch.setattr(worker_tasks, "_resolve_metadata_llm_provider_for_owner", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_tasks, "_resolve_ocr_llm_provider_for_owner", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_tasks, "parse_document_blob", fail_parse_document_blob)

    try:
        worker_tasks.parse_document_task(
            document_id="doc-fail",
            blob_uri="incoming/scan.pdf",
            filename="scan.pdf",
            content_type="application/pdf",
        )
    except RuntimeError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("parse_document_task should re-raise parse failures")

    updated = repository.get("doc-fail")
    assert updated is not None
    assert updated.status == DocumentStatus.FAILED
    history = repository.list_history("doc-fail")
    assert history
    assert history[0].event_type.value == "processing_failed"
    assert history[0].changes["status"]["after"] == "failed"
    assert "OpenRouter" in history[0].changes["error"]["message"]
    assert "vision-capable model" in history[0].changes["error"]["message"]
    assert "Raw error: LLM OCR failed: HTTP 404 from OpenRouter" in history[0].changes["error"]["message"]


def test_parse_document_task_skips_duplicate_ready_document(monkeypatch) -> None:
    repository = InMemoryDocumentRepository()
    document = Document(
        id="doc-1",
        filename="image.jpg",
        owner_id="user-1",
        blob_uri="processed/doc-1/doc-1_image.jpg",
        checksum_sha256="abc123",
        content_type="image/jpeg",
        size_bytes=123,
        status=DocumentStatus.READY,
        created_at=datetime.now(UTC),
    )
    repository.save(document)
    repository.save_parse_result(
        ParseResult(
            document_id="doc-1",
            parser="stub-llm-ocr-separate",
            status="parsed",
            size_bytes=123,
            page_count=1,
            text_preview="sample text",
            created_at=datetime.now(UTC),
        )
    )

    parse_calls = {"count": 0}

    def fake_parse_document_blob(**kwargs):
        del kwargs
        parse_calls["count"] += 1
        raise AssertionError("parse_document_blob should not be called for already-ready documents")

    monkeypatch.setattr(worker_tasks, "_build_repository", lambda: repository)
    monkeypatch.setattr(worker_tasks, "parse_document_blob", fake_parse_document_blob)

    result = worker_tasks.parse_document_task(
        document_id="doc-1",
        blob_uri="incoming/doc-1_image.jpg",
        filename="image.jpg",
        content_type="image/jpeg",
    )

    updated = repository.get("doc-1")
    assert updated is not None
    assert updated.status == DocumentStatus.READY
    assert parse_calls["count"] == 0
    assert result == {
        "document_id": "doc-1",
        "bytes": 123,
        "parser": "stub-llm-ocr-separate",
        "status": "ready",
    }
