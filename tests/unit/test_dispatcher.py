from types import SimpleNamespace

from zapis.infrastructure.dispatchers.celery_ingestion_dispatcher import (
    CeleryIngestionDispatcher,
)


def test_celery_ingestion_dispatcher_enqueues_and_returns_job_id(monkeypatch) -> None:
    class FakeTask:
        called_with: str | None = None

        @classmethod
        def delay(cls, document_id: str):
            cls.called_with = document_id
            return SimpleNamespace(id="celery-job-1")

    monkeypatch.setattr(
        "zapis.infrastructure.dispatchers.celery_ingestion_dispatcher.ingest_document_task",
        FakeTask,
    )

    dispatcher = CeleryIngestionDispatcher()
    job_id = dispatcher.enqueue("doc-1")

    assert job_id == "celery-job-1"
    assert FakeTask.called_with == "doc-1"

