from types import SimpleNamespace

from zapis.infrastructure.dispatchers.celery_ingestion_dispatcher import (
    CeleryIngestionDispatcher,
)


def test_celery_ingestion_dispatcher_enqueues_and_returns_job_id(monkeypatch) -> None:
    class FakeTask:
        called_with: dict | None = None

        @classmethod
        def delay(cls, **kwargs):
            cls.called_with = kwargs
            return SimpleNamespace(id="celery-job-1")

    monkeypatch.setattr(
        "zapis.infrastructure.dispatchers.celery_ingestion_dispatcher.ingest_document_task",
        FakeTask,
    )

    dispatcher = CeleryIngestionDispatcher()
    job_id = dispatcher.enqueue(
        document_id="doc-1",
        blob_uri="file:///tmp/doc-1.pdf",
        filename="doc-1.pdf",
        content_type="application/pdf",
    )

    assert job_id == "celery-job-1"
    assert FakeTask.called_with == {
        "document_id": "doc-1",
        "blob_uri": "file:///tmp/doc-1.pdf",
        "filename": "doc-1.pdf",
        "content_type": "application/pdf",
    }
