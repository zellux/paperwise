from __future__ import annotations

from typing import Any

GROUNDED_QA_SYSTEM_PROMPT = (
    "You are a strict document QA assistant. Answer ONLY from provided context chunks. "
    "Do not use outside knowledge. If evidence is insufficient, set insufficient_evidence=true and explain briefly. "
    "Return strict JSON with keys: answer, insufficient_evidence, citations. "
    "Each citation must include: chunk_id, document_id, title, quote."
)


def build_grounded_qa_user_prompt(*, question: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
    trimmed_contexts: list[dict[str, Any]] = []
    for item in contexts[:30]:
        trimmed_contexts.append(
            {
                "chunk_id": str(item.get("chunk_id", "")),
                "document_id": str(item.get("document_id", "")),
                "title": str(item.get("title", "")),
                "content": str(item.get("content", ""))[:2500],
            }
        )
    return {
        "question": question,
        "contexts": trimmed_contexts,
        "instructions": (
            "Use only these contexts. Cite chunk IDs supporting the answer. "
            "If conflicting evidence exists, mention uncertainty and cite both."
        ),
    }


def extract_grounded_qa_result(parsed: dict[str, Any]) -> dict[str, Any]:
    answer = str(parsed.get("answer", "")).strip()
    insufficient_raw = parsed.get("insufficient_evidence", False)
    insufficient = bool(insufficient_raw)
    citations_raw = parsed.get("citations", [])

    citations: list[dict[str, str]] = []
    if isinstance(citations_raw, list):
        for item in citations_raw:
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id", "")).strip()
            document_id = str(item.get("document_id", "")).strip()
            title = str(item.get("title", "")).strip()
            quote = str(item.get("quote", "")).strip()
            if not chunk_id and not document_id:
                continue
            citations.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "title": title,
                    "quote": quote,
                }
            )

    return {
        "answer": answer,
        "insufficient_evidence": insufficient,
        "citations": citations,
    }
