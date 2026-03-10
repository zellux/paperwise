import re
from pathlib import Path
from typing import Any

from paperwise.application.interfaces import LLMProvider


class SimpleLLMProvider(LLMProvider):
    """Deterministic local provider used until remote LLM integration is wired."""

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        del existing_correspondents
        del existing_document_types
        del existing_tags

        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
        title = re.sub(r"\s+", " ", title).title() or "Untitled Document"

        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text_preview)

        text = f"{filename} {text_preview}".lower()
        if "credit" in text or "experian" in text:
            document_type = "Credit Report"
            correspondent = "Experian"
            tags = ["Credit", "Report"]
        elif "invoice" in text:
            document_type = "Invoice"
            correspondent = "Unknown Vendor"
            tags = ["Invoice"]
        elif "vaccine" in text or "immunization" in text:
            document_type = "Medical Record"
            correspondent = "Healthcare Provider"
            tags = ["Medical", "Health"]
        else:
            document_type = "General Document"
            correspondent = "Unknown Sender"
            tags = ["Document"]

        result: dict[str, Any] = {
            "suggested_title": title,
            "correspondent": correspondent,
            "document_type": document_type,
            "tags": tags,
        }
        if date_match:
            result["document_date"] = date_match.group(1)
        return result
