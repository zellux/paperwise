from zapis.application.interfaces import IngestionDispatcher
from zapis.workers.tasks import ingest_document_task


class CeleryIngestionDispatcher(IngestionDispatcher):
    def enqueue(self, document_id: str) -> str:
        result = ingest_document_task.delay(document_id)
        return str(result.id)

