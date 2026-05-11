from datetime import UTC, datetime
import base64
from html import unescape
import logging
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.parsing_ocr_details import (
    mark_ocr_attempt as _mark_ocr_attempt,
    new_ocr_details as _new_ocr_details,
    set_final_ocr_source as _set_final_ocr_source,
    set_ocr_process_details as _set_ocr_process_details,
)
from paperwise.application.services.parsing_support import (
    fit_preview_text as _fit_preview_text,
    is_good_local_ocr_text as _is_good_local_ocr_text,
    is_high_quality_extracted_text as _is_high_quality_extracted_text,
    select_pdf_page_numbers as _select_pdf_page_numbers,
    strip_nul as _strip_nul,
)
from paperwise.domain.models import ParseResult
from paperwise.infrastructure.config import get_settings
from paperwise.application.services.storage_paths import blob_ref_to_path

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional runtime dependency
    PdfReader = None


logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_MIME_TYPES_BY_SUFFIX = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
SUPPORTED_IMAGE_MIME_TYPES = frozenset(SUPPORTED_IMAGE_MIME_TYPES_BY_SUFFIX.values())


def _normalize_content_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _resolve_supported_image_mime_type(*, suffix: str, content_type: str | None) -> str | None:
    normalized_content_type = _normalize_content_type(content_type)
    if normalized_content_type in SUPPORTED_IMAGE_MIME_TYPES:
        return normalized_content_type
    return SUPPORTED_IMAGE_MIME_TYPES_BY_SUFFIX.get(suffix)


def _build_image_data_url(*, raw: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _extract_text_like_segments(raw: bytes, *, max_chars: int) -> str:
    # Heuristic text extraction from binary-heavy files (for stub OCR readability).
    decoded = raw.decode("latin-1", errors="ignore").replace("\x00", " ")
    segments = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s,.;:()/#&'\"+\-]{2,}", decoded)
    cleaned: list[str] = []
    for segment in segments:
        collapsed = " ".join(segment.split())
        if len(collapsed) < 3:
            continue
        alpha = sum(ch.isalpha() for ch in collapsed)
        if alpha == 0:
            continue
        if alpha / max(len(collapsed), 1) < 0.2:
            continue
        cleaned.append(collapsed)
    if not cleaned:
        return " ".join(decoded.split())[:max_chars]
    return " ".join(cleaned)[:max_chars]


def _extract_pdf_text(
    *,
    blob_path,
    raw: bytes,
    max_chars: int,
) -> tuple[str, int]:
    page_count = raw.count(b"/Type /Page")
    if page_count == 0:
        page_count = 1

    if PdfReader is not None:
        try:
            reader = PdfReader(str(blob_path))
            page_count = max(1, len(reader.pages))
            parts: list[str] = []
            for page in reader.pages:
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                parts.append(text)
            extracted = _fit_preview_text("\n\n".join(parts), max_chars=max_chars)
            if extracted:
                return extracted, page_count
        except Exception as exc:
            logger.warning("PDF text extraction via pypdf failed for %s: %s", blob_path, exc)

    sample = raw[:16000]
    if sample:
        printable = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b <= 126)
        if printable / len(sample) >= 0.8:
            decoded = sample.decode("utf-8", errors="ignore").replace("\x00", " ").strip()
            if decoded:
                return _fit_preview_text(re.sub(r"\s+", " ", decoded), max_chars=max_chars), page_count

    return "", page_count


def _extract_with_local_tesseract(
    *,
    blob_path,
    is_pdf: bool,
    max_chars: int,
) -> str:
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract executable not found.")

    extracted_chunks: list[str] = []

    if is_pdf:
        pdftoppm = shutil.which("pdftoppm")
        if pdftoppm is None:
            raise RuntimeError("pdftoppm executable not found for PDF rasterization.")
        page_count = 0
        if PdfReader is not None:
            try:
                page_count = max(1, len(PdfReader(str(blob_path)).pages))
            except Exception:
                page_count = 0
        if page_count <= 0:
            raw = blob_path.read_bytes()
            page_count = raw.count(b"/Type /Page") or 1
        selected_pages = _select_pdf_page_numbers(page_count=page_count, max_pages=3)
        with TemporaryDirectory(prefix="paperwise-ocr-") as temp_dir:
            image_paths: list[Path] = []
            for page_number in selected_pages:
                out_prefix = f"{temp_dir}/page-{page_number}"
                subprocess.run(
                    [
                        pdftoppm,
                        "-f",
                        str(page_number),
                        "-l",
                        str(page_number),
                        "-png",
                        str(blob_path),
                        out_prefix,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                image_paths.extend(sorted(Path(temp_dir).glob(f"page-{page_number}-*.png")))
            if not image_paths:
                raise RuntimeError("No rasterized PDF pages generated for OCR.")
            for image_path in image_paths:
                proc = subprocess.run(
                    ["tesseract", str(image_path), "stdout"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                chunk = proc.stdout.strip()
                if chunk:
                    extracted_chunks.append(chunk)
    else:
        proc = subprocess.run(
            ["tesseract", str(blob_path), "stdout"],
            check=True,
            capture_output=True,
            text=True,
        )
        chunk = proc.stdout.strip()
        if chunk:
            extracted_chunks.append(chunk)

    combined = "\n\n".join(extracted_chunks).strip()
    return _fit_preview_text(combined, max_chars=max_chars)


def _render_pdf_pages_to_data_urls(
    *,
    blob_path,
    max_pages: int = 3,
) -> list[str]:
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise RuntimeError("pdftoppm executable not found for PDF image rendering.")

    with TemporaryDirectory(prefix="paperwise-vision-") as temp_dir:
        page_count = 0
        if PdfReader is not None:
            try:
                page_count = max(1, len(PdfReader(str(blob_path)).pages))
            except Exception:
                page_count = 0
        if page_count <= 0:
            raw = blob_path.read_bytes()
            page_count = raw.count(b"/Type /Page") or 1
        selected_pages = _select_pdf_page_numbers(page_count=page_count, max_pages=max_pages)
        image_paths: list[Path] = []
        for page_number in selected_pages:
            out_prefix = f"{temp_dir}/page-{page_number}"
            subprocess.run(
                [
                    pdftoppm,
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-png",
                    str(blob_path),
                    out_prefix,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            image_paths.extend(sorted(Path(temp_dir).glob(f"page-{page_number}-*.png")))
        if not image_paths:
            raise RuntimeError("No PDF pages were rendered for LLM OCR.")
        data_urls: list[str] = []
        for image_path in image_paths[:max_pages]:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            data_urls.append(f"data:image/png;base64,{encoded}")
        return data_urls


def parse_document_blob(
    document_id: str,
    blob_uri: str,
    *,
    content_type: str | None = None,
    ocr_provider: str = "llm",
    llm_provider: LLMProvider | None = None,
    ocr_auto_switch: bool = False,
) -> ParseResult:
    """Stub parser for local blob content until real OCR/extract pipeline lands."""
    settings = get_settings()
    blob_path = blob_ref_to_path(blob_uri, settings.object_store_root)
    if blob_path is None:
        raise ValueError(f"Unsupported blob reference: {blob_uri}")
    raw = blob_path.read_bytes()
    normalized_ocr = str(ocr_provider).strip().lower()
    suffix = blob_path.suffix.lower()
    normalized_content_type = _normalize_content_type(content_type)
    supported_image_mime_type = _resolve_supported_image_mime_type(
        suffix=suffix,
        content_type=normalized_content_type,
    )
    ocr_details = _new_ocr_details(
        requested_provider=normalized_ocr,
        auto_switch_enabled=bool(ocr_auto_switch),
    )
    final_text_source = ""

    is_pdf = raw.startswith(b"%PDF") or suffix == ".pdf"
    is_supported_image = supported_image_mime_type is not None
    if is_pdf:
        if normalized_ocr == "tesseract":
            page_count = raw.count(b"/Type /Page")
            if page_count == 0:
                page_count = 1
            _mark_ocr_attempt(ocr_details, "local_tesseract", attempted=True)
            text_preview = _extract_with_local_tesseract(
                blob_path=blob_path,
                is_pdf=True,
                max_chars=6000,
            )
            _mark_ocr_attempt(
                ocr_details,
                "local_tesseract",
                succeeded=bool(text_preview.strip()),
                selected=True,
                chars=len(text_preview),
            )
            final_text_source = "local_tesseract"
        else:
            # Keep a higher preview limit for LLM-driven OCR mode.
            is_llm_ocr = normalized_ocr in {"llm", "llm_separate"}
            preview_limit = 8000 if is_llm_ocr else 6000
            text_preview, page_count = _extract_pdf_text(
                blob_path=blob_path,
                raw=raw,
                max_chars=preview_limit,
            )
            _mark_ocr_attempt(
                ocr_details,
                "text_extraction",
                attempted=True,
                succeeded=bool(text_preview.strip()),
                chars=len(text_preview),
                quality="high" if _is_high_quality_extracted_text(text_preview) else "low",
            )
            final_text_source = "pdf_text_extraction"
    elif suffix in {".txt", ".md", ".markdown"}:
        text_preview = raw[:4000].decode("utf-8", errors="replace").replace("\x00", "")
        page_count = max(1, text_preview.count("\n\n") + 1) if text_preview.strip() else 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
        )
        final_text_source = "plain_text_read"
    elif suffix == ".docx":
        try:
            with ZipFile(blob_path) as zip_file:
                xml = zip_file.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"</w:p>", "\n", xml)
            text = re.sub(r"<[^>]+>", "", text)
            text_preview = unescape(text).replace("\x00", "").strip()
            if not text_preview:
                text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
            page_count = max(1, text.count("\n") // 30 + 1)
        except (KeyError, BadZipFile):
            text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
            page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
        )
        final_text_source = "docx_text_read"
    elif is_supported_image:
        text_preview = _extract_text_like_segments(raw, max_chars=400)
        if normalized_ocr == "tesseract":
            _mark_ocr_attempt(ocr_details, "local_tesseract", attempted=True)
            text_preview = _extract_with_local_tesseract(
                blob_path=blob_path,
                is_pdf=False,
                max_chars=4000,
            )
            _mark_ocr_attempt(
                ocr_details,
                "local_tesseract",
                succeeded=bool(text_preview.strip()),
                selected=True,
                chars=len(text_preview),
            )
            final_text_source = "local_tesseract"
        else:
            _mark_ocr_attempt(
                ocr_details,
                "text_extraction",
                attempted=True,
                succeeded=bool(text_preview.strip()),
                chars=len(text_preview),
                quality="heuristic_image",
            )
            final_text_source = "image_binary_preview"
        page_count = 1
    else:
        text_preview = raw[:200].decode("latin-1", errors="ignore").replace("\x00", "")
        if normalized_ocr == "tesseract":
            _mark_ocr_attempt(ocr_details, "local_tesseract", attempted=True)
            text_preview = _extract_with_local_tesseract(
                blob_path=blob_path,
                is_pdf=False,
                max_chars=4000,
            )
            _mark_ocr_attempt(
                ocr_details,
                "local_tesseract",
                succeeded=bool(text_preview.strip()),
                selected=True,
                chars=len(text_preview),
            )
            final_text_source = "local_tesseract"
        else:
            _mark_ocr_attempt(
                ocr_details,
                "text_extraction",
                attempted=True,
                succeeded=bool(text_preview.strip()),
                chars=len(text_preview),
                quality="heuristic",
            )
            final_text_source = "binary_text_preview"
        page_count = 1

    if normalized_ocr in {"llm", "llm_separate"}:
        extract_images_method = (
            getattr(llm_provider, "extract_ocr_text_from_images", None) if llm_provider is not None else None
        )
        if ocr_auto_switch:
            _mark_ocr_attempt(ocr_details, "local_tesseract", attempted=True)
            try:
                local_ocr_text = _extract_with_local_tesseract(
                    blob_path=blob_path,
                    is_pdf=is_pdf,
                    max_chars=8000 if is_pdf else 4000,
                )
                _mark_ocr_attempt(
                    ocr_details,
                    "local_tesseract",
                    succeeded=bool(local_ocr_text.strip()),
                    chars=len(local_ocr_text),
                    quality_passed=_is_good_local_ocr_text(local_ocr_text, text_preview),
                )
            except Exception:
                local_ocr_text = ""
                _mark_ocr_attempt(
                    ocr_details,
                    "local_tesseract",
                    succeeded=False,
                    error="local_tesseract_unavailable_or_failed",
                )
            if _is_good_local_ocr_text(local_ocr_text, text_preview):
                parser_name = "auto-local-tesseract"
                _mark_ocr_attempt(ocr_details, "local_tesseract", selected=True)
                cleaned_preview = _strip_nul(local_ocr_text)
                _set_final_ocr_source(
                    ocr_details,
                    source="local_tesseract_auto_switch",
                    text_preview=cleaned_preview,
                )
                _set_ocr_process_details(
                    ocr_details,
                    llm_provider=llm_provider,
                    text_preview=cleaned_preview,
                )
                return ParseResult(
                    document_id=document_id,
                    parser=parser_name,
                    status="parsed",
                    size_bytes=len(raw),
                    page_count=page_count,
                    text_preview=cleaned_preview,
                    created_at=datetime.now(UTC),
                    ocr_details=ocr_details,
                )
        used_image_ocr = False
        if (is_pdf or is_supported_image) and callable(extract_images_method):
            image_data_urls: list[str] = []
            render_error: Exception | None = None
            if is_pdf:
                logger.info("Rendering PDF pages for vision OCR: %s", blob_path)
                try:
                    image_data_urls = _render_pdf_pages_to_data_urls(blob_path=blob_path, max_pages=3)
                except Exception as exc:
                    render_error = exc
                    _mark_ocr_attempt(
                        ocr_details,
                        "llm_vision",
                        attempted=True,
                        succeeded=False,
                        rendered_pages=0,
                        error=f"pdf_render_failed: {exc}",
                    )
                    logger.warning(
                        "PDF page rendering failed for %s; trying text OCR fallback: %s",
                        blob_path,
                        exc,
                    )
            else:
                logger.info("Using uploaded image directly for vision OCR: %s", blob_path)
                image_data_urls = [
                    _build_image_data_url(
                        raw=raw,
                        mime_type=supported_image_mime_type or "image/png",
                    )
                ]
            if render_error is None:
                _mark_ocr_attempt(
                    ocr_details,
                    "llm_vision",
                    attempted=True,
                    rendered_pages=len(image_data_urls),
                )
                logger.info(
                    "Rendered %d PDF/image page(s) for vision OCR: %s",
                    len(image_data_urls),
                    blob_path,
                )
                try:
                    ocr_text = extract_images_method(
                        filename=blob_path.name,
                        image_data_urls=image_data_urls,
                    )
                    if not isinstance(ocr_text, str) or not ocr_text.strip():
                        raise RuntimeError("LLM OCR failed: provider returned empty OCR text.")
                    text_preview = ocr_text.strip()
                    used_image_ocr = True
                    _mark_ocr_attempt(
                        ocr_details,
                        "llm_vision",
                        succeeded=True,
                        selected=True,
                        chars=len(text_preview),
                    )
                    final_text_source = "llm_vision_ocr"
                except Exception as exc:
                    _mark_ocr_attempt(
                        ocr_details,
                        "llm_vision",
                        succeeded=False,
                        error=str(exc),
                    )
                    if "timed out" in str(exc).lower():
                        # Keep pipeline moving when vision OCR times out on large/complex PDFs.
                        logger.warning("Vision OCR timed out for %s; using extracted text fallback.", blob_path)
                    else:
                        raise RuntimeError(f"LLM OCR failed: {exc}") from exc
        extract_method = getattr(llm_provider, "extract_ocr_text", None) if llm_provider is not None else None
        if callable(extract_method) and not used_image_ocr:
            if not text_preview.strip():
                raise RuntimeError(
                    "No readable text was extracted from this file before OCR. "
                    "Use Local Tesseract OCR for image-only/scanned PDFs."
                )
            _mark_ocr_attempt(ocr_details, "llm_text", attempted=True)
            try:
                ocr_text = extract_method(
                    filename=blob_path.name,
                    content_type=(
                        "application/pdf"
                        if is_pdf
                        else supported_image_mime_type or normalized_content_type or "text/plain"
                    ),
                    text_preview=text_preview,
                )
                if isinstance(ocr_text, str) and ocr_text.strip():
                    text_preview = ocr_text.strip()
                    _mark_ocr_attempt(
                        ocr_details,
                        "llm_text",
                        succeeded=True,
                        selected=True,
                        chars=len(text_preview),
                    )
                    final_text_source = "llm_text_ocr"
                else:
                    raise RuntimeError("OCR provider returned empty OCR text.")
            except Exception as exc:
                _mark_ocr_attempt(
                    ocr_details,
                    "llm_text",
                    succeeded=False,
                    error=str(exc),
                )
                if "timed out" in str(exc).lower():
                    # Fall back to extracted text to avoid blocking document processing.
                    logger.warning("LLM OCR timed out for %s; using extracted text fallback.", blob_path)
                else:
                    raise RuntimeError(f"LLM OCR failed: {exc}") from exc

    parser_name = "stub-local"
    if normalized_ocr == "llm":
        parser_name = "stub-llm-ocr"
    elif normalized_ocr == "llm_separate":
        parser_name = "stub-llm-ocr-separate"
    elif normalized_ocr == "tesseract":
        parser_name = "local-tesseract-ocr"

    text_preview = _strip_nul(text_preview)
    _set_final_ocr_source(
        ocr_details,
        source=final_text_source or parser_name,
        text_preview=text_preview,
    )
    _set_ocr_process_details(
        ocr_details,
        llm_provider=llm_provider,
        text_preview=text_preview,
    )
    return ParseResult(
        document_id=document_id,
        parser=parser_name,
        status="parsed",
        size_bytes=len(raw),
        page_count=page_count,
        text_preview=text_preview,
        created_at=datetime.now(UTC),
        ocr_details=ocr_details,
    )
