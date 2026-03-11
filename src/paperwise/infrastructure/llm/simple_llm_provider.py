import re
from pathlib import Path
from typing import Any

from paperwise.application.interfaces import LLMProvider


class SimpleLLMProvider(LLMProvider):
    """Deterministic local provider used until remote LLM integration is wired."""

    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        return " ".join(text_preview.split())

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        del current_correspondent
        del current_document_type
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

    def answer_grounded(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        terms = {part.lower() for part in re.findall(r"[A-Za-z0-9]{2,}", question)}
        for ctx in contexts:
            content = str(ctx.get("content", ""))
            lowered = content.lower()
            if not terms or any(term in lowered for term in terms):
                snippet = " ".join(content.split())[:240]
                return {
                    "answer": snippet or "No answer content in context.",
                    "insufficient_evidence": False,
                    "citations": [
                        {
                            "chunk_id": str(ctx.get("chunk_id", "")),
                            "document_id": str(ctx.get("document_id", "")),
                            "title": str(ctx.get("title", "")),
                            "quote": snippet,
                        }
                    ],
                }
        return {
            "answer": "Not enough evidence in the selected documents.",
            "insufficient_evidence": True,
            "citations": [],
        }

    def rewrite_retrieval_queries(
        self,
        *,
        question: str,
    ) -> dict[str, Any]:
        compact = " ".join(str(question or "").split()).strip()
        tokens = [token for token in re.findall(r"[A-Za-z0-9]{2,}", compact.lower())]
        unique: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            unique.append(token)
        base = compact or "document search"
        queries = [base]
        if unique:
            queries.append(" ".join(unique[:6]))
        return {
            "queries": queries[:3],
            "must_terms": unique[:5],
            "anchor_terms": unique[:3],
            "optional_terms": [],
        }
