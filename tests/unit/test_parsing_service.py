from pathlib import Path

import pytest

from paperwise.application.services import parsing as parsing_module
from paperwise.application.services.parsing import parse_document_blob


class RecordingOCRLLM:
    def __init__(self, ocr_text: str) -> None:
        self.ocr_text = ocr_text
        self.calls = 0
        self.image_calls = 0

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
        del image_data_urls
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


def test_parse_document_blob_auto_switch_uses_llm_for_low_quality_text(tmp_path, monkeypatch) -> None:
    blob = tmp_path / "low-quality.pdf"
    blob.write_bytes(b"%PDF-1.7\nshort\n/Type /Page")
    llm = RecordingOCRLLM("LLM OCR output used")

    monkeypatch.setattr(parsing_module, "_extract_with_local_tesseract", lambda **kwargs: "tiny")

    result = parse_document_blob(
        document_id="doc-1",
        blob_uri=blob.as_uri(),
        ocr_provider="llm",
        llm_provider=llm,
        ocr_auto_switch=True,
    )

    assert llm.calls == 1
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
