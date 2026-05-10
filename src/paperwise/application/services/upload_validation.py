from pathlib import Path


SUPPORTED_UPLOAD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".markdown",
    ".md",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
}
SUPPORTED_UPLOAD_CONTENT_TYPES = {
    "application/msword",
    "application/octet-stream",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/markdown",
    "text/plain",
}


def normalize_content_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def is_supported_upload(*, filename: str, content_type: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    normalized_content_type = normalize_content_type(content_type)
    if suffix in SUPPORTED_UPLOAD_EXTENSIONS:
        return True
    return normalized_content_type in SUPPORTED_UPLOAD_CONTENT_TYPES
