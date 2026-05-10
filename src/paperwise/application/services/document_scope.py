from paperwise.application.interfaces import DocumentStore
from paperwise.domain.models import User


def all_owned_document_ids(repository: DocumentStore, current_user: User) -> list[str]:
    document_ids: list[str] = []
    batch_size = 1000
    offset = 0
    while True:
        rows = repository.list_owner_documents_with_llm_results(
            owner_id=current_user.id,
            limit=batch_size,
            offset=offset,
        )
        if not rows:
            break
        document_ids.extend(document.id for document, _llm_result in rows)
        if len(rows) < batch_size:
            break
        offset += batch_size
    return document_ids
