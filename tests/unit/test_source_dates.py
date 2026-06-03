from datetime import UTC, datetime
import json
from zipfile import ZipFile

from pypdf import PdfWriter

from paperwise.application.services import source_dates as source_dates_module
from paperwise.application.services.source_dates import extract_source_document_date
from paperwise.domain.models import Document, DocumentStatus


def _document_for_path(path) -> Document:
    return Document(
        id="doc-source-date",
        filename=path.name,
        owner_id="user-source-date",
        blob_uri=path.as_uri(),
        checksum_sha256="abc123",
        content_type="application/octet-stream",
        size_bytes=path.stat().st_size,
        status=DocumentStatus.PROCESSING,
        created_at=datetime(2026, 5, 13, tzinfo=UTC),
    )


def test_extract_source_document_date_uses_pdf_creation_date(tmp_path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/CreationDate": "D:20240305010203Z"})
    with pdf_path.open("wb") as handle:
        writer.write(handle)

    assert extract_source_document_date(_document_for_path(pdf_path)) == "2024-03-05"


def test_extract_source_document_date_falls_back_when_pypdf_date_property_fails(monkeypatch, tmp_path) -> None:
    class FakeMetadata(dict):
        @property
        def creation_date(self):
            raise ValueError("Can not convert date: 2/7/2020 05:41:45")

        @property
        def modification_date(self):
            return None

    class FakeReader:
        def __init__(self, path: str) -> None:
            del path
            self.metadata = FakeMetadata({"/CreationDate": "2/7/2020 05:41:45"})

    pdf_path = tmp_path / "statement.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")
    monkeypatch.setattr(source_dates_module, "PdfReader", FakeReader)

    assert extract_source_document_date(_document_for_path(pdf_path)) == "2020-02-07"


def test_extract_source_document_date_uses_docx_core_created_date(tmp_path) -> None:
    docx_path = tmp_path / "letter.docx"
    with ZipFile(docx_path, "w") as zip_file:
        zip_file.writestr(
            "docProps/core.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dcterms="http://purl.org/dc/terms/">'
                '<dcterms:created>2024-04-06T12:30:00Z</dcterms:created>'
                "</cp:coreProperties>"
            ),
        )

    assert extract_source_document_date(_document_for_path(docx_path)) == "2024-04-06"


def test_extract_source_document_date_accepts_docx_common_slash_date(tmp_path) -> None:
    docx_path = tmp_path / "letter.docx"
    with ZipFile(docx_path, "w") as zip_file:
        zip_file.writestr(
            "docProps/core.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dcterms="http://purl.org/dc/terms/">'
                '<dcterms:created>2/7/2020 05:41:45</dcterms:created>'
                "</cp:coreProperties>"
            ),
        )

    assert extract_source_document_date(_document_for_path(docx_path)) == "2020-02-07"


def test_extract_source_document_date_uses_upload_last_modified_sidecar(tmp_path) -> None:
    file_path = tmp_path / "upload.txt"
    file_path.write_text("notes", encoding="utf-8")
    metadata_path = file_path.with_name(f"{file_path.stem}.metadata.json")
    metadata_path.write_text(
        json.dumps({"source_last_modified_at": "2024-05-07T08:09:10.000Z"}),
        encoding="utf-8",
    )

    assert extract_source_document_date(_document_for_path(file_path)) == "2024-05-07"


def test_extract_source_document_date_accepts_upload_sidecar_common_slash_date(tmp_path) -> None:
    file_path = tmp_path / "upload.txt"
    file_path.write_text("notes", encoding="utf-8")
    metadata_path = file_path.with_name(f"{file_path.stem}.metadata.json")
    metadata_path.write_text(
        json.dumps({"source_last_modified_at": "2/7/2020 05:41:45"}),
        encoding="utf-8",
    )

    assert extract_source_document_date(_document_for_path(file_path)) == "2020-02-07"


def test_extract_source_document_date_ignores_upload_time_when_no_source_date_exists(tmp_path) -> None:
    file_path = tmp_path / "upload.txt"
    file_path.write_text("notes", encoding="utf-8")
    metadata_path = file_path.with_name(f"{file_path.stem}.metadata.json")
    metadata_path.write_text(
        json.dumps({"stored_at": "2026-05-13T12:00:00+00:00"}),
        encoding="utf-8",
    )

    assert extract_source_document_date(_document_for_path(file_path)) is None


def test_extract_source_document_date_ignores_invalid_embedded_and_sidecar_dates(tmp_path) -> None:
    docx_path = tmp_path / "letter.docx"
    with ZipFile(docx_path, "w") as zip_file:
        zip_file.writestr(
            "docProps/core.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dcterms="http://purl.org/dc/terms/">'
                "<dcterms:created>not-a-date</dcterms:created>"
                "</cp:coreProperties>"
            ),
        )
    metadata_path = docx_path.with_name(f"{docx_path.stem}.metadata.json")
    metadata_path.write_text(
        json.dumps({"source_last_modified_at": "also-not-a-date"}),
        encoding="utf-8",
    )

    assert extract_source_document_date(_document_for_path(docx_path)) is None
