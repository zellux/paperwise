from datetime import UTC, datetime

from paperwise.application.services.document_pipeline import process_document
from paperwise.domain.models import Document, DocumentStatus, HistoryActorType, ParseResult
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository


class FakeMetadataLLMProvider:
    model = "fake-metadata"

    def suggest_metadata(self, **kwargs):
        del kwargs
        return {
            "suggested_title": "Pipeline Invoice",
            "document_date": "2026-05-10",
            "correspondent": "Acme Billing",
            "document_type": "Invoice",
            "tags": ["finance", "pipeline"],
            "llm_total_tokens": 17,
        }


def test_process_document_persists_outputs_history_chunks_and_processed_blob(tmp_path, monkeypatch) -> None:
    object_store_root = tmp_path / "object-store"
    incoming_dir = object_store_root / "incoming"
    incoming_dir.mkdir(parents=True)
    incoming_path = incoming_dir / "invoice.pdf"
    incoming_path.write_bytes(b"%PDF-1.4\n% fake fixture\n")

    repository = InMemoryDocumentRepository()
    document = Document(
        id="doc-pipeline",
        filename="invoice.pdf",
        owner_id="user-1",
        blob_uri="incoming/invoice.pdf",
        checksum_sha256="abc123",
        content_type="application/pdf",
        size_bytes=incoming_path.stat().st_size,
        status=DocumentStatus.PROCESSING,
        created_at=datetime.now(UTC),
    )
    repository.save(document)

    def fake_parse_document_blob(**kwargs):
        assert kwargs["blob_uri"] == "incoming/invoice.pdf"
        return ParseResult(
            document_id="doc-pipeline",
            parser="fake-parser",
            status="parsed",
            size_bytes=incoming_path.stat().st_size,
            page_count=2,
            text_preview="invoice total amount due payment terms",
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        "paperwise.application.services.document_pipeline.parse_document_blob",
        fake_parse_document_blob,
    )

    result = process_document(
        document=document,
        repository=repository,
        object_store_root=object_store_root,
        metadata_llm_provider=FakeMetadataLLMProvider(),
        ocr_provider="tesseract",
        ocr_llm_provider=None,
        ocr_auto_switch=False,
        actor_type=HistoryActorType.SYSTEM,
        actor_id=None,
        history_source="test.pipeline",
    )

    updated = repository.get("doc-pipeline")
    assert updated is not None
    assert updated.status == DocumentStatus.READY
    assert updated.blob_uri.startswith("processed/doc-pipeline/")
    assert (object_store_root / updated.blob_uri).exists()
    assert not incoming_path.exists()

    assert repository.get_parse_result("doc-pipeline") == result.parse_result
    llm_result = repository.get_llm_parse_result("doc-pipeline")
    assert llm_result is not None
    assert llm_result.suggested_title == "Pipeline Invoice"
    assert llm_result.llm_total_tokens == 17
    assert result.indexed_chunk_count == 1
    assert len(repository.list_document_chunks("doc-pipeline")) == 1

    history_types = [event.event_type.value for event in repository.list_history("doc-pipeline", limit=20)]
    assert "metadata_changed" in history_types
    assert "processing_completed" in history_types
    assert "file_moved" in history_types
