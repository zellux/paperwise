from pathlib import Path


SUPPORTED_UPLOAD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".csv",
    ".gif",
    ".jpeg",
    ".jpg",
    ".markdown",
    ".md",
    ".odp",
    ".ods",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".png",
    ".rtf",
    ".tif",
    ".tiff",
    ".tsv",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
}
SUPPORTED_UPLOAD_CONTENT_TYPES = {
    "application/msword",
    "application/octet-stream",
    "application/pdf",
    "application/rtf",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-rtf",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
    "text/csv",
    "text/markdown",
    "text/plain",
    "text/rtf",
    "text/tab-separated-values",
}


def normalize_content_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def is_supported_upload(*, filename: str, content_type: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    normalized_content_type = normalize_content_type(content_type)
    if suffix in SUPPORTED_UPLOAD_EXTENSIONS:
        return True
    return normalized_content_type in SUPPORTED_UPLOAD_CONTENT_TYPES
