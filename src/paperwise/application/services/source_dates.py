from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from paperwise.application.services.document_file_cleanup import metadata_paths_for_blob_path
from paperwise.application.services.metadata_updates import validate_document_date
from paperwise.application.services.storage_paths import blob_ref_to_path
from paperwise.domain.models import Document
from paperwise.infrastructure.config import get_settings

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional runtime dependency
    PdfReader = None


def extract_source_document_date(document: Document) -> str | None:
    blob_path = blob_ref_to_path(document.blob_uri, get_settings().object_store_root)
    if blob_path is None or not blob_path.exists() or not blob_path.is_file():
        return None
    return _embedded_file_date(blob_path) or _uploaded_file_date(blob_path)


def _embedded_file_date(blob_path: Path) -> str | None:
    suffix = blob_path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_date(blob_path)
    if suffix == ".docx":
        return _docx_date(blob_path)
    return None


def _pdf_date(blob_path: Path) -> str | None:
    if PdfReader is None:
        return None
    try:
        metadata = PdfReader(str(blob_path)).metadata
    except Exception:
        return None
    if metadata is None:
        return None
    for key in ("creation_date", "modification_date"):
        value = getattr(metadata, key, None)
        parsed = _date_from_unknown_value(value)
        if parsed:
            return parsed
    for key in ("/CreationDate", "/ModDate"):
        parsed = _date_from_unknown_value(metadata.get(key))
        if parsed:
            return parsed
    return None


def _docx_date(blob_path: Path) -> str | None:
    try:
        with ZipFile(blob_path) as zip_file:
            raw = zip_file.read("docProps/core.xml")
    except (BadZipFile, KeyError, OSError):
        return None
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return None
    for tag_name in ("created", "modified"):
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] != tag_name:
                continue
            parsed = _date_from_unknown_value(element.text)
            if parsed:
                return parsed
    return None


def _uploaded_file_date(blob_path: Path) -> str | None:
    for metadata_path in metadata_paths_for_blob_path(blob_path):
        if not metadata_path.exists() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("source_last_modified_at", "source_last_modified_ms"):
            parsed = _date_from_unknown_value(metadata.get(key))
            if parsed:
                return parsed
    return None


def _date_from_unknown_value(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC).date().isoformat() if value.tzinfo else value.date().isoformat()
    if isinstance(value, int | float):
        if value <= 0:
            return None
        try:
            return datetime.fromtimestamp(value / 1000, tz=UTC).date().isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    validated = validate_document_date(text[:10])
    if validated:
        return validated
    if text.startswith("D:"):
        match = re.match(r"D:(\d{4})(\d{2})?(\d{2})?", text)
        if match:
            year, month, day = match.groups()
            return validate_document_date(f"{year}-{month or '01'}-{day or '01'}")
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        return None
