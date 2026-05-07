import json

from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.storage_paths import path_to_blob_ref


def test_move_blob_to_processed_truncates_for_metadata_sidecar(tmp_path) -> None:
    root_dir = tmp_path / "object-store"
    source_path = root_dir / "incoming" / "2026" / "04" / "21" / "upload.pdf"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"%PDF-long-name")
    blob_uri = path_to_blob_ref(source_path, str(root_dir))
    original_filename = (
        "04212026_Hospital Bill Complaint Program You may receive separate statements from "
        "The Hospital Bill Complaint Program is a state program, which reviews hospital "
        "decisions about whether you qualify for help pa.pdf"
    )

    processed_uri = move_blob_to_processed(
        blob_uri=blob_uri,
        object_store_root=str(root_dir),
        document_id="00000000-0000-0000-0000-000000000000",
        original_filename=original_filename,
        content_type="application/pdf",
        checksum_sha256="abc123",
        size_bytes=14,
    )

    target_path = root_dir / processed_uri
    metadata_path = target_path.with_name(f"{target_path.name}.metadata.json")
    assert target_path.exists()
    assert metadata_path.exists()
    assert target_path.name.endswith(".pdf")
    assert len(metadata_path.name.encode("utf-8")) <= 255
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["original_filename"] == original_filename
