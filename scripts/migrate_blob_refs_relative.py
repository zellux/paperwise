#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from paperwise.application.services.storage_paths import blob_ref_to_path, path_to_blob_ref
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.db import build_engine, build_session_factory
from paperwise.infrastructure.repositories.postgres_models import DocumentRow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert document blob_uri values to relative object-store paths.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run).",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.repository_backend.lower() != "postgres":
        raise SystemExit(
            f"Repository backend is {settings.repository_backend!r}; set PAPERWISE_REPOSITORY_BACKEND=postgres.",
        )

    root_dir = Path(settings.object_store_root).expanduser().resolve()
    engine = build_engine(settings.postgres_url)
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        rows = session.scalars(select(DocumentRow)).all()
        updated = 0
        skipped = 0

        for row in rows:
            resolved = blob_ref_to_path(row.blob_uri, str(root_dir))
            if resolved is None:
                skipped += 1
                continue
            target_ref = path_to_blob_ref(resolved, str(root_dir))
            if row.blob_uri == target_ref:
                continue
            if args.apply:
                row.blob_uri = target_ref
            updated += 1

        if args.apply:
            session.commit()

    mode = "apply" if args.apply else "dry-run"
    print(f"mode={mode}")
    print(f"documents_total={len(rows)}")
    print(f"documents_to_update={updated}")
    print(f"documents_skipped={skipped}")


if __name__ == "__main__":
    main()

