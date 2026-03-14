from __future__ import annotations

import argparse

from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.repositories.in_memory_document_repository import InMemoryDocumentRepository
from paperwise.infrastructure.repositories.postgres_document_repository import PostgresDocumentRepository


def _build_repository():
    settings = get_settings()
    if settings.repository_backend.lower() == "postgres":
        return PostgresDocumentRepository(settings.postgres_url)
    return InMemoryDocumentRepository()


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild document chunk index from parse results.")
    parser.add_argument("--owner-id", default="", help="Optional owner filter")
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum documents to process")
    args = parser.parse_args()

    repository = _build_repository()
    offset = 0
    batch_size = 200
    processed = 0
    indexed_docs = 0
    indexed_chunks = 0

    while True:
        docs = repository.list_documents(limit=batch_size, offset=offset)
        if not docs:
            break
        for document in docs:
            if args.owner_id and document.owner_id != args.owner_id:
                continue
            parse_result = repository.get_parse_result(document.id)
            if parse_result is None:
                continue
            chunk_count = index_document_chunks(
                repository=repository,
                document=document,
                parse_result=parse_result,
            )
            indexed_docs += 1
            indexed_chunks += chunk_count
            processed += 1
            if args.limit > 0 and processed >= args.limit:
                print(f"Indexed documents: {indexed_docs}")
                print(f"Indexed chunks: {indexed_chunks}")
                return 0
        if len(docs) < batch_size:
            break
        offset += batch_size

    print(f"Indexed documents: {indexed_docs}")
    print(f"Indexed chunks: {indexed_chunks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
