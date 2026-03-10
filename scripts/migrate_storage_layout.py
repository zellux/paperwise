#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)


def _sanitize_filename(value: str) -> str:
    cleaned = Path(value).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        return "uploaded-document.bin"
    return cleaned


def _metadata_filename(blob_filename: str) -> str:
    return f"{blob_filename}.metadata.json"


@dataclass
class MovePlan:
    document_id: str
    source_path: Path
    target_path: Path
    old_blob_uri: str


def _build_target_path(root_dir: Path, *, document_id: str, created_at: datetime, filename: str) -> Path:
    created_utc = created_at.astimezone(UTC)
    date_path = created_utc.strftime("%Y/%m/%d")
    sanitized = _sanitize_filename(filename)
    target_name = f"{document_id}_{sanitized}"
    return root_dir / "incoming" / date_path / target_name


def _build_plans(*, root_dir: Path, repository: PostgresDocumentRepository) -> tuple[list[MovePlan], int]:
    documents = repository.list_documents(limit=1_000_000)
    plans: list[MovePlan] = []
    skipped_non_file = 0

    for document in documents:
        parsed = urlparse(document.blob_uri)
        if parsed.scheme != "file":
            skipped_non_file += 1
            continue
        source_path = Path(unquote(parsed.path))
        target_path = _build_target_path(
            root_dir,
            document_id=document.id,
            created_at=document.created_at,
            filename=document.filename,
        )
        plans.append(
            MovePlan(
                document_id=document.id,
                source_path=source_path,
                target_path=target_path,
                old_blob_uri=document.blob_uri,
            )
        )
    return plans, skipped_non_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate local object-store files into incoming/YYYY/MM/DD/<doc_id>_<filename> layout.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, runs as dry-run.",
    )
    args = parser.parse_args()

    settings = get_settings()
    root_dir = Path(settings.object_store_root).expanduser().resolve()
    repository = PostgresDocumentRepository(settings.postgres_url)

    plans, skipped_non_file = _build_plans(root_dir=root_dir, repository=repository)
    missing_sources = [plan for plan in plans if not plan.source_path.exists()]
    executable = [plan for plan in plans if plan.source_path.exists()]

    print(f"root_dir={root_dir}")
    print(f"documents_with_file_uri={len(plans)}")
    print(f"skipped_non_file_uri={skipped_non_file}")
    print(f"missing_source_files={len(missing_sources)}")
    print(f"planned_moves={len(executable)}")

    if not args.apply:
        print("dry-run mode; use --apply to move files and update blob_uri.")
        for plan in executable[:10]:
            print(f"- {plan.source_path} -> {plan.target_path}")
        return

    moved = 0
    copied_from_prior_move = 0
    updated = 0
    unchanged = 0
    skipped_runtime_missing = 0
    moved_source_targets: dict[Path, Path] = {}

    docs_by_id = {doc.id: doc for doc in repository.list_documents(limit=1_000_000)}

    for plan in executable:
        document = docs_by_id.get(plan.document_id)
        if document is None:
            continue

        target_path = plan.target_path
        if target_path.exists() and target_path.resolve() != plan.source_path.resolve():
            target_path = target_path.with_name(
                f"{plan.document_id}_{document.checksum_sha256[:12]}_{_sanitize_filename(document.filename)}"
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if plan.source_path.exists():
            if plan.source_path.resolve() != target_path.resolve():
                shutil.move(str(plan.source_path), str(target_path))
                moved += 1
            else:
                unchanged += 1
            moved_source_targets[plan.source_path] = target_path
        else:
            prior_target = moved_source_targets.get(plan.source_path)
            if prior_target is None or not prior_target.exists():
                skipped_runtime_missing += 1
                continue
            if not target_path.exists():
                shutil.copy2(str(prior_target), str(target_path))
                copied_from_prior_move += 1

        metadata_path = target_path.with_name(_metadata_filename(target_path.name))
        metadata = {
            "original_filename": document.filename,
            "content_type": document.content_type,
            "checksum_sha256": document.checksum_sha256,
            "size_bytes": document.size_bytes,
            "stored_key": str(target_path.relative_to(root_dir)),
            "stored_at": document.created_at.isoformat(),
            "migrated_from_blob_uri": plan.old_blob_uri,
            "migrated_at": datetime.now(UTC).isoformat(),
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

        new_blob_uri = target_path.resolve().as_uri()
        if document.blob_uri != new_blob_uri:
            document.blob_uri = new_blob_uri
            repository.save(document)
            updated += 1

    print(f"moved_files={moved}")
    print(f"copied_from_prior_move={copied_from_prior_move}")
    print(f"unchanged_files={unchanged}")
    print(f"skipped_runtime_missing={skipped_runtime_missing}")
    print(f"updated_documents={updated}")


if __name__ == "__main__":
    main()
