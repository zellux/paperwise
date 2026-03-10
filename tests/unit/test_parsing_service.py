from pathlib import Path

import pytest

from paperwise.application.services.parsing import parse_document_blob


class RecordingOCRLLM:
    def __init__(self, ocr_text: str) -> None:
        self.ocr_text = ocr_text
        self.calls = 0

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


def test_parse_document_blob_uses_llm_ocr_when_configured(tmp_path) -> None:
    blob = tmp_path / "sample.pdf"
    blob.write_bytes(b"%PDF-1.7\nFake content for OCR\n/Type /Page")
    llm = RecordingOCRLLM("Structured OCR text")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
    )

    assert llm.calls == 1
    assert result.text_preview == "Structured OCR text"
    assert result.parser == "stub-llm-ocr"


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


def test_parse_document_blob_llm_mode_raises_when_no_readable_text(tmp_path) -> None:
    blob = tmp_path / "scan.pdf"
    blob.write_bytes(b"%PDF-1.7\n" + bytes([0, 159, 200, 10]) * 400)
    llm = RecordingOCRLLM("unused")

    with pytest.raises(RuntimeError, match="No readable text was extracted"):
        parse_document_blob(
            document_id="doc-1",
            blob_uri=blob.as_uri(),
            ocr_provider="llm",
            llm_provider=llm,
        )
