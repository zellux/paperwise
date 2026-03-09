from zapis.application.interfaces import IngestionDispatcher
from zapis.workers.tasks import ingest_document_task


class CeleryIngestionDispatcher(IngestionDispatcher):
    def enqueue(
        self,
        document_id: str,
        blob_uri: str,
        filename: str,
        content_type: str,
    ) -> str:
        result = ingest_document_task.delay(
            document_id=document_id,
            blob_uri=blob_uri,
            filename=filename,
            content_type=content_type,
        )
        return str(result.id)
