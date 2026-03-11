from __future__ import annotations

from typing import Any

RETRIEVAL_QUERY_SYSTEM_PROMPT = (
    "You rewrite user questions for document retrieval. "
    "Return strict JSON with keys: queries, must_terms, optional_terms. "
    "queries must be 3 to 6 short retrieval queries preserving user intent and entities. "
    "must_terms should include critical anchors (names, exact concepts) if present. "
    "optional_terms should include synonyms, abbreviations, and unit variants."
)


def build_retrieval_query_user_prompt(*, question: str) -> dict[str, Any]:
    return {
        "question": question,
        "instructions": (
            "Do not answer the question. Generate retrieval queries only. "
            "Preserve entities and key constraints. "
            "For measurements, include unit-aware variants (lb/lbs/kg, in/inches/cm)."
        ),
    }


def extract_retrieval_query_result(parsed: dict[str, Any], *, fallback_question: str) -> dict[str, Any]:
    queries_raw = parsed.get("queries", [])
    must_terms_raw = parsed.get("must_terms", [])
    optional_terms_raw = parsed.get("optional_terms", [])

    def _clean_list(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in values:
            value = " ".join(str(item or "").split()).strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(value)
        return cleaned

    queries = _clean_list(queries_raw)[:6]
    must_terms = _clean_list(must_terms_raw)[:12]
    optional_terms = _clean_list(optional_terms_raw)[:18]

    if not queries:
        base = " ".join(str(fallback_question or "").split()).strip()
        if base:
            queries = [base]

    return {
        "queries": queries,
        "must_terms": must_terms,
        "optional_terms": optional_terms,
    }

