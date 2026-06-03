from datetime import UTC, datetime
import base64
import csv
from html import unescape
import io
import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
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
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}
SUPPORTED_IMAGE_MIME_TYPES = frozenset(SUPPORTED_IMAGE_MIME_TYPES_BY_SUFFIX.values())
PPTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DIRECT_TEXT_CONTENT_TYPES_BY_SUFFIX = {
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": PPTX_CONTENT_TYPE,
    ".rtf": "application/rtf",
    ".tsv": "text/tab-separated-values",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
TEXT_DOCUMENT_SUFFIXES = frozenset(
    {".markdown", ".md", ".txt", *DIRECT_TEXT_CONTENT_TYPES_BY_SUFFIX.keys()}
)
TEXT_DOCUMENT_CONTENT_TYPES = frozenset(
    {
        *DIRECT_TEXT_CONTENT_TYPES_BY_SUFFIX.values(),
        "application/vnd.oasis.opendocument.graphics",
        "application/vnd.oasis.opendocument.graphics-template",
        "application/vnd.oasis.opendocument.presentation-template",
        "application/vnd.oasis.opendocument.spreadsheet-template",
        "application/vnd.oasis.opendocument.text-template",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/x-rtf",
        "text/markdown",
        "text/plain",
        "text/rtf",
    }
)


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


def _is_text_native_document(*, suffix: str, content_type: str | None) -> bool:
    return suffix in TEXT_DOCUMENT_SUFFIXES or _normalize_content_type(content_type) in TEXT_DOCUMENT_CONTENT_TYPES


def _decode_text_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1"):
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        cleaned = decoded.replace("\x00", "").strip()
        if cleaned:
            return cleaned
    return raw.decode("utf-8", errors="replace").replace("\x00", "").strip()


def _extract_provider_ocr_text(value: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("{"):
        return text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    ocr_text = parsed.get("ocr_text") if isinstance(parsed, dict) else None
    if isinstance(ocr_text, str) and ocr_text.strip():
        return ocr_text.strip()
    return text


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


def _extract_plain_text(raw: bytes, *, max_chars: int) -> str:
    return _fit_preview_text(_decode_text_bytes(raw), max_chars=max_chars)


def _extract_delimited_text(raw: bytes, *, delimiter: str, max_chars: int) -> str:
    decoded = _decode_text_bytes(raw)
    reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
    rows: list[str] = []
    try:
        for row in reader:
            cleaned = [cell.strip() for cell in row]
            if any(cleaned):
                rows.append("\t".join(cleaned))
    except csv.Error:
        return _fit_preview_text(decoded, max_chars=max_chars)
    return _fit_preview_text("\n".join(rows), max_chars=max_chars)


def _xml_local_name(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _extract_xml_text_runs(xml: str, *, text_tags: set[str] | None = None) -> str:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        text = re.sub(r"<[^>]+>", "\n", xml)
        return "\n".join(part.strip() for part in unescape(text).splitlines() if part.strip())

    parts: list[str] = []
    wanted = text_tags or {"t"}
    for node in root.iter():
        if _xml_local_name(node.tag) in wanted and node.text:
            text = node.text.strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _numeric_path_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)\.xml$", name)
    if match:
        return int(match.group(1)), name
    return 0, name


def _extract_word_xml_text(xml: str) -> str:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        text = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"</w:tr>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return unescape(text).replace("\x00", "").strip()

    paragraphs: list[str] = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        parts: list[str] = []
        for node in paragraph.iter():
            tag = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""
            if tag == "t" and node.text:
                parts.append(node.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag in {"br", "cr"}:
                parts.append("\n")
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs).strip()


def _extract_docx_text(*, blob_path: Path, raw: bytes, max_chars: int) -> tuple[str, int]:
    try:
        with ZipFile(blob_path) as zip_file:
            xml = zip_file.read("word/document.xml").decode("utf-8", errors="ignore")
        text_preview = _fit_preview_text(_extract_word_xml_text(xml), max_chars=max_chars)
        if text_preview:
            return text_preview, 1
    except (KeyError, BadZipFile):
        pass
    return _fit_preview_text(_decode_text_bytes(raw), max_chars=400), 1


def _extract_rtf_text(raw: bytes, *, max_chars: int) -> str:
    source = _decode_text_bytes(raw)
    source = re.sub(
        r"\\'([0-9a-fA-F]{2})",
        lambda match: bytes.fromhex(match.group(1)).decode("cp1252", errors="replace"),
        source,
    )
    source = re.sub(
        r"\\u(-?\d+)\??",
        lambda match: chr(int(match.group(1)) % 65536),
        source,
    )
    source = re.sub(r"\\(?:par|line)\b ?", "\n", source)
    source = re.sub(r"\\tab\b ?", "\t", source)
    source = re.sub(r"\\[a-zA-Z]+\d* ?|\\.", "", source)
    source = source.replace("{", "").replace("}", "")
    return _fit_preview_text("\n".join(line.strip() for line in source.splitlines() if line.strip()), max_chars=max_chars)


def _extract_shared_string_text(node: ElementTree.Element) -> str:
    parts: list[str] = []
    for child in node.iter():
        if _xml_local_name(child.tag) == "t" and child.text:
            parts.append(child.text)
    return "".join(parts).strip()


def _extract_xlsx_text(*, blob_path: Path, raw: bytes, max_chars: int) -> tuple[str, int]:
    try:
        with ZipFile(blob_path) as zip_file:
            shared_strings: list[str] = []
            try:
                shared_root = ElementTree.fromstring(zip_file.read("xl/sharedStrings.xml"))
                shared_strings = [_extract_shared_string_text(node) for node in shared_root if _xml_local_name(node.tag) == "si"]
            except (KeyError, ElementTree.ParseError):
                shared_strings = []

            sheet_names = sorted(
                (name for name in zip_file.namelist() if re.match(r"^xl/worksheets/sheet\d+\.xml$", name)),
                key=_numeric_path_sort_key,
            )
            sheets: list[str] = []
            for index, sheet_name in enumerate(sheet_names, start=1):
                try:
                    root = ElementTree.fromstring(zip_file.read(sheet_name))
                except ElementTree.ParseError:
                    continue
                lines = [f"Sheet {index}"]
                for row in root.iter():
                    if _xml_local_name(row.tag) != "row":
                        continue
                    cells: list[str] = []
                    for cell in row:
                        if _xml_local_name(cell.tag) != "c":
                            continue
                        cell_type = cell.attrib.get("t", "")
                        value = ""
                        if cell_type == "inlineStr":
                            value = _extract_shared_string_text(cell)
                        else:
                            value_node = next((child for child in cell if _xml_local_name(child.tag) == "v"), None)
                            if value_node is not None and value_node.text is not None:
                                value = value_node.text.strip()
                                if cell_type == "s":
                                    try:
                                        value = shared_strings[int(value)]
                                    except (IndexError, ValueError):
                                        pass
                        if value:
                            cells.append(value)
                    if cells:
                        lines.append("\t".join(cells))
                if len(lines) > 1:
                    sheets.append("\n".join(lines))
            text_preview = _fit_preview_text("\n\n".join(sheets), max_chars=max_chars)
            if text_preview:
                return text_preview, max(1, len(sheet_names))
    except BadZipFile:
        pass
    return _extract_text_like_segments(raw, max_chars=max_chars), 1


def _extract_open_document_text(*, blob_path: Path, raw: bytes, max_chars: int) -> tuple[str, int]:
    try:
        with ZipFile(blob_path) as zip_file:
            xml = zip_file.read("content.xml").decode("utf-8", errors="ignore")
    except (BadZipFile, KeyError):
        return _extract_text_like_segments(raw, max_chars=max_chars), 1

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return _fit_preview_text(_extract_xml_text_runs(xml, text_tags={"p", "h"}), max_chars=max_chars), 1

    suffix = blob_path.suffix.lower()
    page_count = 1
    blocks: list[str] = []

    if suffix == ".ods":
        tables = [node for node in root.iter() if _xml_local_name(node.tag) == "table"]
        page_count = max(1, len(tables))
        for index, table in enumerate(tables, start=1):
            lines = [table.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name", f"Sheet {index}")]
            for row in table:
                if _xml_local_name(row.tag) != "table-row":
                    continue
                cells: list[str] = []
                for cell in row:
                    if _xml_local_name(cell.tag) not in {"table-cell", "covered-table-cell"}:
                        continue
                    text = " ".join(
                        paragraph.text.strip()
                        for paragraph in cell.iter()
                        if _xml_local_name(paragraph.tag) in {"p", "h"} and paragraph.text and paragraph.text.strip()
                    )
                    if text:
                        cells.append(text)
                if cells:
                    lines.append("\t".join(cells))
            if len(lines) > 1:
                blocks.append("\n".join(lines))
    else:
        if suffix == ".odp":
            page_count = max(1, sum(1 for node in root.iter() if _xml_local_name(node.tag) == "page"))
        for node in root.iter():
            if _xml_local_name(node.tag) not in {"p", "h"}:
                continue
            text = "".join(node.itertext()).strip()
            if text:
                blocks.append(text)

    return _fit_preview_text("\n".join(blocks), max_chars=max_chars), page_count


def _extract_presentation_slide_text(xml: str) -> str:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        text = re.sub(r"<[^>]+>", "\n", xml)
        return "\n".join(part.strip() for part in unescape(text).splitlines() if part.strip())

    parts: list[str] = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""
        if tag == "t" and node.text:
            text = node.text.strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _pptx_slide_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"/slide(\d+)\.xml$", name)
    if match:
        return int(match.group(1)), name
    return 0, name


def _extract_pptx_text(*, blob_path: Path, raw: bytes, max_chars: int) -> tuple[str, int]:
    try:
        with ZipFile(blob_path) as zip_file:
            slide_names = sorted(
                (
                    name
                    for name in zip_file.namelist()
                    if re.match(r"^ppt/slides/slide\d+\.xml$", name)
                ),
                key=_pptx_slide_sort_key,
            )
            slides: list[str] = []
            for slide_name in slide_names:
                xml = zip_file.read(slide_name).decode("utf-8", errors="ignore")
                slide_text = _extract_presentation_slide_text(xml)
                if slide_text:
                    slides.append(slide_text)
            page_count = max(1, len(slide_names))
            text_preview = _fit_preview_text("\n\n".join(slides), max_chars=max_chars)
            if text_preview:
                return text_preview, page_count
    except BadZipFile:
        pass
    return _fit_preview_text(_decode_text_bytes(raw), max_chars=400), 1


def _extract_doc_text(*, blob_path: Path, raw: bytes, max_chars: int) -> str:
    converter_commands: list[list[str]] = []
    textutil = shutil.which("textutil")
    if textutil is not None:
        converter_commands.append([textutil, "-convert", "txt", "-stdout", str(blob_path)])
    antiword = shutil.which("antiword")
    if antiword is not None:
        converter_commands.append([antiword, str(blob_path)])
    catdoc = shutil.which("catdoc")
    if catdoc is not None:
        converter_commands.append([catdoc, str(blob_path)])

    for command in converter_commands:
        try:
            proc = subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=20,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        extracted = _decode_text_bytes(proc.stdout)
        if extracted:
            return _fit_preview_text(extracted, max_chars=max_chars)

    return _extract_text_like_segments(raw, max_chars=max_chars)


def _extract_legacy_office_text(
    *,
    blob_path: Path,
    raw: bytes,
    command_names: tuple[str, ...],
    max_chars: int,
) -> str:
    converter_commands: list[list[str]] = []
    textutil = shutil.which("textutil")
    if textutil is not None:
        converter_commands.append([textutil, "-convert", "txt", "-stdout", str(blob_path)])
    for command_name in command_names:
        command_path = shutil.which(command_name)
        if command_path is not None:
            converter_commands.append([command_path, str(blob_path)])

    for command in converter_commands:
        try:
            proc = subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=20,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        extracted = _decode_text_bytes(proc.stdout)
        if extracted:
            return _fit_preview_text(extracted, max_chars=max_chars)

    return _extract_text_like_segments(raw, max_chars=max_chars)


def _pdf_page_count(blob_path: Path) -> int:
    if PdfReader is not None:
        try:
            return max(1, len(PdfReader(str(blob_path)).pages))
        except Exception:
            pass
    raw = blob_path.read_bytes()
    return raw.count(b"/Type /Page") or 1


def _rasterize_pdf_pages(
    *,
    blob_path: Path,
    max_pages: int,
    output_dir: Path,
) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise RuntimeError("pdftoppm executable not found for PDF rasterization.")

    selected_pages = _select_pdf_page_numbers(
        page_count=_pdf_page_count(blob_path),
        max_pages=max_pages,
    )
    image_paths: list[Path] = []
    for page_number in selected_pages:
        out_prefix = str(output_dir / f"page-{page_number}")
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
        image_paths.extend(sorted(output_dir.glob(f"page-{page_number}-*.png")))
    return image_paths


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
        with TemporaryDirectory(prefix="paperwise-ocr-") as temp_dir:
            image_paths = _rasterize_pdf_pages(
                blob_path=Path(blob_path),
                max_pages=3,
                output_dir=Path(temp_dir),
            )
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
    with TemporaryDirectory(prefix="paperwise-vision-") as temp_dir:
        image_paths = _rasterize_pdf_pages(
            blob_path=Path(blob_path),
            max_pages=max_pages,
            output_dir=Path(temp_dir),
        )
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
    is_text_native_document = _is_text_native_document(
        suffix=suffix,
        content_type=normalized_content_type,
    )
    if is_pdf:
        if normalized_ocr == "tesseract":
            page_count = _pdf_page_count(blob_path)
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
    elif suffix in {".txt", ".md", ".markdown"} or normalized_content_type in {"text/markdown", "text/plain"}:
        text_preview = _extract_plain_text(raw, max_chars=8000)
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
            selected=True,
        )
        final_text_source = "plain_text_read"
    elif suffix in {".csv", ".tsv"} or normalized_content_type in {"text/csv", "text/tab-separated-values"}:
        delimiter = "\t" if suffix == ".tsv" or normalized_content_type == "text/tab-separated-values" else ","
        text_preview = _extract_delimited_text(raw, delimiter=delimiter, max_chars=8000)
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
            selected=True,
        )
        final_text_source = "delimited_text_read"
    elif (
        suffix == ".docx"
        or normalized_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        text_preview, page_count = _extract_docx_text(blob_path=blob_path, raw=raw, max_chars=8000)
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
            selected=True,
        )
        final_text_source = "docx_text_read"
    elif (
        suffix == ".xlsx"
        or normalized_content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        text_preview, page_count = _extract_xlsx_text(blob_path=blob_path, raw=raw, max_chars=8000)
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = "xlsx_text_read"
    elif suffix == ".pptx" or normalized_content_type == PPTX_CONTENT_TYPE:
        text_preview, page_count = _extract_pptx_text(blob_path=blob_path, raw=raw, max_chars=8000)
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text",
            selected=True,
        )
        final_text_source = "pptx_text_read"
    elif suffix in {".odt", ".ods", ".odp"} or normalized_content_type in {
        "application/vnd.oasis.opendocument.presentation",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.text",
    }:
        text_preview, page_count = _extract_open_document_text(blob_path=blob_path, raw=raw, max_chars=8000)
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = f"{suffix.lstrip('.') or 'opendocument'}_text_read"
    elif suffix == ".rtf" or normalized_content_type in {"application/rtf", "application/x-rtf", "text/rtf"}:
        text_preview = _extract_rtf_text(raw, max_chars=8000)
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = "rtf_text_read"
    elif suffix == ".doc" or normalized_content_type == "application/msword":
        text_preview = _extract_doc_text(blob_path=blob_path, raw=raw, max_chars=8000)
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = "doc_text_read"
    elif suffix == ".xls" or normalized_content_type == "application/vnd.ms-excel":
        text_preview = _extract_legacy_office_text(
            blob_path=blob_path,
            raw=raw,
            command_names=("xls2csv",),
            max_chars=8000,
        )
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = "xls_text_read"
    elif suffix == ".ppt" or normalized_content_type == "application/vnd.ms-powerpoint":
        text_preview = _extract_legacy_office_text(
            blob_path=blob_path,
            raw=raw,
            command_names=("catppt",),
            max_chars=8000,
        )
        page_count = 1
        _mark_ocr_attempt(
            ocr_details,
            "text_extraction",
            attempted=True,
            succeeded=bool(text_preview.strip()),
            chars=len(text_preview),
            quality="direct_text" if text_preview.strip() else "empty_direct_text",
            selected=True,
        )
        final_text_source = "ppt_text_read"
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

    if normalized_ocr in {"llm", "llm_separate"} and not is_text_native_document:
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
                    text_preview = _extract_provider_ocr_text(ocr_text)
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
                    text_preview = _extract_provider_ocr_text(ocr_text)
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
    if is_text_native_document:
        parser_name = "direct-text-parser"
    elif normalized_ocr == "llm":
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
