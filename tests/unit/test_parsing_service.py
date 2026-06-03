from pathlib import Path
from zipfile import ZipFile

import pytest

from paperwise.application.services import parsing as parsing_module
from paperwise.application.services.parsing import parse_document_blob


def _write_xlsx_fixture(path: Path) -> None:
    with ZipFile(path, "w") as zip_file:
        zip_file.writestr(
            "xl/sharedStrings.xml",
            (
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<si><t>Invoice</t></si><si><t>Amount</t></si><si><t>Paid</t></si>"
                "<si><t>PW-100</t></si></sst>"
            ),
        )
        zip_file.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<sheetData><row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>'
                '<row><c t="s"><v>3</v></c><c><v>42.50</v></c></row></sheetData></worksheet>'
            ),
        )
        zip_file.writestr(
            "xl/worksheets/sheet2.xml",
            (
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<sheetData><row><c t="inlineStr"><is><t>Status</t></is></c><c t="s"><v>2</v></c></row>'
                "</sheetData></worksheet>"
            ),
        )


def _write_open_document_fixture(path: Path, content_xml: str) -> None:
    with ZipFile(path, "w") as zip_file:
        zip_file.writestr("content.xml", content_xml)


class RecordingOCRLLM:
    def __init__(self, ocr_text: str) -> None:
        self.ocr_text = ocr_text
        self.calls = 0
        self.image_calls = 0
        self.image_data_urls: list[str] = []
        self._model = "test-ocr-model"

    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        del text_preview
        self.calls += 1
        return self.ocr_text

    def extract_ocr_text_from_images(
        self,
        *,
        filename: str,
        image_data_urls: list[str],
    ) -> str:
        del filename
        self.image_data_urls = image_data_urls
        self.image_calls += 1
        return self.ocr_text


class TimeoutOCRLLM:
    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        del text_preview
        raise RuntimeError("The read operation timed out")


class TimeoutImageOCRLLM:
    def extract_ocr_text_from_images(
        self,
        *,
        filename: str,
        image_data_urls: list[str],
    ) -> str:
        del filename
        del image_data_urls
        raise RuntimeError("The read operation timed out")


class TextOnlyOCRLLM:
    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        del text_preview
        return "unused"


def test_fit_preview_text_preserves_head_and_tail_content() -> None:
    preview = parsing_module._fit_preview_text(
        "START " + ("alpha " * 200) + "2026-03-20 END",
        max_chars=120,
    )

    assert preview.startswith("START ")
    assert preview.endswith("2026-03-20 END")
    assert "..." in preview
    assert len(preview) == 120


def test_select_pdf_page_numbers_prioritizes_front_and_back_pages() -> None:
    assert parsing_module._select_pdf_page_numbers(page_count=16, max_pages=3) == [1, 2, 16]
    assert parsing_module._select_pdf_page_numbers(page_count=2, max_pages=3) == [1, 2]


def test_rasterize_pdf_pages_reuses_selected_page_logic(monkeypatch, tmp_path) -> None:
    class FakeReader:
        def __init__(self, path: str) -> None:
            del path
            self.pages = [object(), object(), object(), object()]

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        del kwargs
        calls.append(command)
        Path(f"{command[-1]}-1.png").write_bytes(b"png")

    monkeypatch.setattr(parsing_module, "PdfReader", FakeReader)
    monkeypatch.setattr(parsing_module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(parsing_module.subprocess, "run", fake_run)

    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\n")
    output_dir = tmp_path / "rasterized"
    output_dir.mkdir()

    image_paths = parsing_module._rasterize_pdf_pages(
        blob_path=blob,
        max_pages=3,
        output_dir=output_dir,
    )

    assert [path.name for path in image_paths] == ["page-1-1.png", "page-2-1.png", "page-4-1.png"]
    assert [command[2] for command in calls] == ["1", "2", "4"]


def test_extract_pdf_text_preserves_tail_dates_in_preview(monkeypatch, tmp_path) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, path: str) -> None:
            del path
            self.pages = [
                FakePage("Opening terms " + ("alpha " * 700)),
                FakePage("Closing signature date 2026-03-20"),
            ]

    monkeypatch.setattr(parsing_module, "PdfReader", FakeReader)

    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\n/Type /Page\n/Type /Page\n")

    text_preview, page_count = parsing_module._extract_pdf_text(
        blob_path=blob,
        raw=blob.read_bytes(),
        max_chars=240,
    )

    assert page_count == 2
    assert "Opening terms" in text_preview
    assert "2026-03-20" in text_preview
    assert "..." in text_preview


def test_parse_document_blob_uses_llm_ocr_when_configured(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\nFake content for OCR\n/Type /Page")
    llm = RecordingOCRLLM("Structured OCR text")

    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )
    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.image_calls == 1
    assert llm.calls == 0
    assert result.text_preview == "Structured OCR text"
    assert result.parser == "stub-llm-ocr"
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["text_extraction"]["attempted"] is True
    assert result.ocr_details["attempts"]["llm_vision"]["succeeded"] is True
    assert result.ocr_details["final_text_source"] == "llm_vision_ocr"
    assert result.ocr_details["process"]["location"] == "remote"
    assert result.ocr_details["process"]["engine"] == "llm"
    assert result.ocr_details["process"]["method"] == "llm_vision"
    assert result.ocr_details["process"]["model"] == "test-ocr-model"
    assert result.ocr_details["process"]["result_size_bytes"] == len("Structured OCR text".encode("utf-8"))


def test_parse_document_blob_skips_llm_ocr_for_local_provider(tmp_path) -> None:
    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\nFake content for OCR\n/Type /Page")
    llm = RecordingOCRLLM("should-not-be-used")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=Path(blob).as_uri(),
        ocr_provider="local",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "stub-local"


def test_parse_document_blob_text_file_skips_llm_ocr_when_configured(tmp_path) -> None:
    blob = tmp_path / "notes.txt"
    blob.write_text(
        "Directly readable notes\n\n"
        "Section breaks in plain text are not rendered document pages.\n\n"
        "Still the same text preview.",
        encoding="utf-8",
    )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="text/plain",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert llm.image_calls == 0
    assert result.parser == "direct-text-parser"
    assert "Directly readable notes" in result.text_preview
    assert result.page_count == 1
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["text_extraction"]["selected"] is True
    assert result.ocr_details["attempts"]["llm_text"]["attempted"] is False
    assert result.ocr_details["final_text_source"] == "plain_text_read"


def test_parse_document_blob_docx_extracts_text_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "letter.docx"
    with ZipFile(blob, "w") as zip_file:
        zip_file.writestr(
            "word/document.xml",
            (
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>Policy renewal notice</w:t></w:r></w:p>"
                "<w:p><w:r><w:instrText>HYPERLINK &quot;https://example.com&quot;</w:instrText></w:r>"
                "<w:r><w:t>Coverage starts June 1.</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
        zip_file.writestr(
            "word/footer1.xml",
            (
                '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:p><w:r><w:t>Page 1 of 2</w:t></w:r></w:p></w:ftr>"
            ),
        )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Policy renewal notice" in result.text_preview
    assert "Coverage starts June 1." in result.text_preview
    assert "HYPERLINK" not in result.text_preview
    assert "Page 1 of 2" not in result.text_preview
    assert result.page_count == 1
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "docx_text_read"


def test_parse_document_blob_pptx_extracts_slide_text_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "slides.pptx"
    with ZipFile(blob, "w") as zip_file:
        zip_file.writestr(
            "ppt/slides/slide2.xml",
            (
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Second slide finding</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>Action item</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
            ),
        )
        zip_file.writestr(
            "ppt/slides/slide1.xml",
            (
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>First slide title</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>Opening summary</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
            ),
        )
        zip_file.writestr(
            "ppt/notesSlides/notesSlide1.xml",
            (
                '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                "<a:t>Speaker notes should not appear</a:t></p:notes>"
            ),
        )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert llm.image_calls == 0
    assert result.parser == "direct-text-parser"
    assert result.text_preview.index("First slide title") < result.text_preview.index("Second slide finding")
    assert "Opening summary" in result.text_preview
    assert "Action item" in result.text_preview
    assert "Speaker notes" not in result.text_preview
    assert result.page_count == 2
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "pptx_text_read"


def test_parse_document_blob_doc_uses_direct_binary_text_fallback(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "legacy.doc"
    blob.write_bytes(b"\xd0\xcf\x11\xe0 Legacy Word content Amount due 42.00 USD")
    llm = RecordingOCRLLM("")

    monkeypatch.setattr(parsing_module.shutil, "which", lambda name: None)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/msword",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Legacy Word content" in result.text_preview
    assert "Amount due 42.00 USD" in result.text_preview
    assert result.page_count == 1
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "doc_text_read"


def test_parse_document_blob_csv_extracts_rows_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "ledger.csv"
    blob.write_text('Name,Amount,Note\n"Paperwise, Inc.",19.95,"CSV cell"\n', encoding="utf-8")
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="text/csv",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Name\tAmount\tNote" in result.text_preview
    assert "Paperwise, Inc.\t19.95\tCSV cell" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "delimited_text_read"


def test_parse_document_blob_tsv_extracts_rows_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "ledger.tsv"
    blob.write_text("Name\tAmount\nPaperwise\t24.00\n", encoding="utf-8")
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="text/tab-separated-values",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Name\tAmount" in result.text_preview
    assert "Paperwise\t24.00" in result.text_preview


def test_parse_document_blob_xlsx_extracts_sheet_cell_text_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "ledger.xlsx"
    _write_xlsx_fixture(blob)
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert result.page_count == 2
    assert "Sheet 1" in result.text_preview
    assert "Invoice\tAmount" in result.text_preview
    assert "PW-100\t42.50" in result.text_preview
    assert "Status\tPaid" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "xlsx_text_read"


def test_parse_document_blob_xls_uses_direct_binary_text_fallback(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "legacy.xls"
    blob.write_bytes(b"\xd0\xcf\x11\xe0 Legacy Excel workbook Revenue total 123.45")
    llm = RecordingOCRLLM("")

    monkeypatch.setattr(parsing_module.shutil, "which", lambda name: None)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.ms-excel",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Legacy Excel workbook" in result.text_preview
    assert "Revenue total 123.45" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "xls_text_read"


def test_parse_document_blob_rtf_extracts_plain_text_without_llm_ocr(tmp_path) -> None:
    blob = tmp_path / "memo.rtf"
    blob.write_text(r"{\rtf1\ansi Policy memo\par Renewal amount \b 42\b0 \par}", encoding="utf-8")
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/rtf",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Policy memo" in result.text_preview
    assert "Renewal amount 42" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "rtf_text_read"


def test_parse_document_blob_open_document_text_extracts_content(tmp_path) -> None:
    blob = tmp_path / "letter.odt"
    _write_open_document_fixture(
        blob,
        (
            '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            "<office:body><office:text><text:h>Policy packet</text:h>"
            "<text:p>OpenDocument text body</text:p></office:text></office:body></office:document-content>"
        ),
    )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.oasis.opendocument.text",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Policy packet" in result.text_preview
    assert "OpenDocument text body" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "odt_text_read"


def test_parse_document_blob_open_document_spreadsheet_extracts_cells(tmp_path) -> None:
    blob = tmp_path / "sheet.ods"
    _write_open_document_fixture(
        blob,
        (
            '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            '<office:body><office:spreadsheet><table:table table:name="Budget">'
            "<table:table-row><table:table-cell><text:p>Category</text:p></table:table-cell>"
            "<table:table-cell><text:p>Total</text:p></table:table-cell></table:table-row>"
            "<table:table-row><table:table-cell><text:p>Supplies</text:p></table:table-cell>"
            "<table:table-cell><text:p>88.00</text:p></table:table-cell></table:table-row>"
            "</table:table></office:spreadsheet></office:body></office:document-content>"
        ),
    )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.oasis.opendocument.spreadsheet",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert result.page_count == 1
    assert "Budget" in result.text_preview
    assert "Category\tTotal" in result.text_preview
    assert "Supplies\t88.00" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "ods_text_read"


def test_parse_document_blob_open_document_presentation_extracts_slide_text(tmp_path) -> None:
    blob = tmp_path / "deck.odp"
    _write_open_document_fixture(
        blob,
        (
            '<office:document-content xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            "<office:body><office:presentation><draw:page><text:p>First ODP slide</text:p></draw:page>"
            "<draw:page><text:p>Second ODP slide</text:p></draw:page></office:presentation></office:body>"
            "</office:document-content>"
        ),
    )
    llm = RecordingOCRLLM("")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.oasis.opendocument.presentation",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert result.page_count == 2
    assert "First ODP slide" in result.text_preview
    assert "Second ODP slide" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "odp_text_read"


def test_parse_document_blob_ppt_uses_direct_binary_text_fallback(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "legacy.ppt"
    blob.write_bytes(b"\xd0\xcf\x11\xe0 Legacy PowerPoint deck Slide title Roadmap")
    llm = RecordingOCRLLM("")

    monkeypatch.setattr(parsing_module.shutil, "which", lambda name: None)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="application/vnd.ms-powerpoint",
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 0
    assert result.parser == "direct-text-parser"
    assert "Legacy PowerPoint deck" in result.text_preview
    assert "Slide title Roadmap" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["final_text_source"] == "ppt_text_read"


def test_parse_document_blob_llm_mode_raises_when_no_readable_text(tmp_path) -> None:
    blob = tmp_path / "scan.pdf"
    blob.write_bytes(b"%PDF-1.7\n" + bytes([0, 159, 200, 10]) * 400)
    llm = TextOnlyOCRLLM()

    with pytest.raises(RuntimeError, match="No readable text was extracted"):
        parse_document_blob(
            document_id="doc-1",
            blob_uri=blob.as_uri(),
            ocr_provider="llm",
            llm_provider=llm,
        )


def test_parse_document_blob_llm_timeout_falls_back_to_extracted_text(tmp_path) -> None:
    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\nReadable sample OCR text\n/Type /Page")
    llm = TimeoutOCRLLM()

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert result.parser == "stub-llm-ocr"
    assert "Readable sample OCR text" in result.text_preview


def test_parse_document_blob_pdf_render_failure_uses_text_ocr_fallback(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\nReadable sample OCR text\n/Type /Page")
    llm = RecordingOCRLLM('{"ocr_text": "Text OCR fallback"}')

    def fail_render(**kwargs):
        del kwargs
        raise RuntimeError("pdftoppm failed")

    monkeypatch.setattr(parsing_module, "_render_pdf_pages_to_data_urls", fail_render)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.image_calls == 0
    assert llm.calls == 1
    assert result.text_preview == "Text OCR fallback"
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["llm_vision"]["succeeded"] is False
    assert result.ocr_details["attempts"]["llm_text"]["succeeded"] is True


def test_parse_document_blob_auto_switch_uses_llm_for_low_quality_text(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "low-quality.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("LLM OCR output used")

    monkeypatch.setattr(parsing_module, "_extract_with_local_tesseract", lambda **kwargs: "tiny")
    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=True,
    )

    assert llm.image_calls == 1
    assert llm.calls == 0
    assert result.parser == "stub-llm-ocr"
    assert result.text_preview == "LLM OCR output used"


def test_parse_document_blob_auto_switch_uses_good_local_ocr_and_skips_llm(
    tmp_path, monkeypatch
) -> None:
    blob = tmp_path / "scan.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("LLM OCR output should be skipped")
    local_text = (
        "This local OCR result is detailed and readable with many words and full lines. " * 8
    ).strip()

    monkeypatch.setattr(parsing_module, "_extract_with_local_tesseract", lambda **kwargs: local_text)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=True,
    )

    assert llm.calls == 0
    assert result.parser == "auto-local-tesseract"
    assert result.text_preview == local_text
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["local_tesseract"]["selected"] is True
    assert result.ocr_details["final_text_source"] == "local_tesseract_auto_switch"
    assert result.ocr_details["process"]["location"] == "local"
    assert result.ocr_details["process"]["engine"] == "tesseract"
    assert result.ocr_details["process"]["model"] is None
    assert result.ocr_details["process"]["result_size_bytes"] == len(local_text.encode("utf-8"))


def test_parse_document_blob_auto_switch_uses_matching_local_ocr_and_skips_llm(
    tmp_path, monkeypatch
) -> None:
    blob = tmp_path / "invoice.pdf"
    extracted_text = (
        "Invoice Invoice number IN-2061643 Date of issue May 7, 2024 "
        "Date due May 7, 2024 Cloudflare Inc 101 Townsend Street "
        "San Francisco California 94107 United States Bill to Yuanxuan Wang "
        "Amount due 0.00 USD"
    )
    blob.write_bytes(b"%PDF-1.7\nplaceholder\n/Type /Page")
    llm = RecordingOCRLLM("LLM OCR output should be skipped")
    local_text = (
        "Invoice\nInvoice number IN-2061643\nDate of issue May 7, 2024\n"
        "Date due May 7, 2024\nCloudflare, Inc.\n101 Townsend Street\n"
        "San Francisco, California 94107\nUnited States\nBill to Yuanxuan Wang\n"
        "Amount due $0.00 USD"
    )

    monkeypatch.setattr(
        parsing_module,
        "_extract_pdf_text",
        lambda **kwargs: (extracted_text, 1),
    )
    monkeypatch.setattr(parsing_module, "_extract_with_local_tesseract", lambda **kwargs: local_text)

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=True,
    )

    assert llm.image_calls == 0
    assert llm.calls == 0
    assert result.parser == "auto-local-tesseract"
    assert result.text_preview == local_text
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["local_tesseract"]["quality_passed"] is True
    assert result.ocr_details["attempts"]["local_tesseract"]["selected"] is True
    assert result.ocr_details["final_text_source"] == "local_tesseract_auto_switch"


def test_parse_document_blob_auto_switch_off_does_not_run_local_ocr(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "manual-llm.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("LLM OCR output used")
    local_calls = {"count": 0}

    def _fake_local_ocr(**kwargs):
        del kwargs
        local_calls["count"] += 1
        return "Strong local OCR text that should not be used"

    monkeypatch.setattr(parsing_module, "_extract_with_local_tesseract", _fake_local_ocr)
    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert local_calls["count"] == 0
    assert llm.image_calls == 1
    assert llm.calls == 0
    assert result.parser == "stub-llm-ocr"


def test_parse_document_blob_auto_switch_off_pdf_uses_image_ocr_path(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "vision.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("Vision OCR output used")

    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert llm.image_calls == 1
    assert llm.calls == 0
    assert result.parser == "stub-llm-ocr"
    assert result.text_preview == "Vision OCR output used"


def test_parse_document_blob_tesseract_pdf_uses_reader_page_count(tmp_path, monkeypatch) -> None:
    pypdf = pytest.importorskip("pypdf")
    blob = tmp_path / "multipage.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    with blob.open("wb") as handle:
        writer.write(handle)

    monkeypatch.setattr(
        parsing_module,
        "_extract_with_local_tesseract",
        lambda **kwargs: "Tesseract text",
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="tesseract",
        ocr_auto_switch=False,
    )

    assert result.page_count == 3
    assert result.text_preview == "Tesseract text"


def test_parse_document_blob_image_uses_llm_image_ocr_path(tmp_path) -> None:
    blob = tmp_path / "camera-scan"
    blob.write_bytes(b"\x89PNG\r\n\x1a\nFake image bytes")
    llm = RecordingOCRLLM("Vision OCR text from image")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="image/png",
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert llm.image_calls == 1
    assert llm.calls == 0
    assert result.parser == "stub-llm-ocr"
    assert result.page_count == 1
    assert result.text_preview == "Vision OCR text from image"
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["llm_vision"]["attempted"] is True
    assert result.ocr_details["attempts"]["llm_vision"]["succeeded"] is True
    assert result.ocr_details["final_text_source"] == "llm_vision_ocr"


def test_parse_document_blob_tiff_uses_llm_image_ocr_path(tmp_path) -> None:
    blob = tmp_path / "scan.tiff"
    blob.write_bytes(b"II*\x00Fake tiff image bytes")
    llm = RecordingOCRLLM("Vision OCR text from TIFF")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        content_type="image/tiff",
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert llm.image_calls == 1
    assert llm.calls == 0
    assert llm.image_data_urls[0].startswith("data:image/tiff;base64,")
    assert result.parser == "stub-llm-ocr"
    assert result.page_count == 1
    assert result.text_preview == "Vision OCR text from TIFF"
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["llm_vision"]["attempted"] is True
    assert result.ocr_details["attempts"]["llm_vision"]["succeeded"] is True
    assert result.ocr_details["final_text_source"] == "llm_vision_ocr"


def test_parse_document_blob_image_ocr_timeout_falls_back_to_extracted_text(
    tmp_path, monkeypatch
) -> None:
    blob = tmp_path / "vision-timeout.pdf"
    blob.write_bytes(b"%PDF-1.7\nReadable sample OCR text\n/Type /Page")
    llm = TimeoutImageOCRLLM()

    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert result.parser == "stub-llm-ocr"
    assert "Readable sample OCR text" in result.text_preview
    assert result.ocr_details is not None
    assert result.ocr_details["attempts"]["llm_vision"]["attempted"] is True
    assert result.ocr_details["attempts"]["llm_vision"]["succeeded"] is False
    assert result.ocr_details["final_text_source"] == "pdf_text_extraction"


def test_parse_document_blob_strips_nul_bytes_from_ocr_result(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "vision-nul.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("alpha\x00beta")

    monkeypatch.setattr(
        parsing_module,
        "_render_pdf_pages_to_data_urls",
        lambda **kwargs: ["data:image/png;base64,abc"],
    )

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=False,
    )

    assert result.text_preview == "alphabeta"
