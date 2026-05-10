import re
from typing import Any

CHAT_SEARCH_CONTEXT_MAX_CHARS = 1800
CHAT_CONTEXT_PREFIX_CHARS = 420


def compact_chat_context_content(content: str, query: str) -> tuple[str, bool]:
    text = str(content or "")
    if len(text) <= CHAT_SEARCH_CONTEXT_MAX_CHARS:
        return text, False
    lowered = text.casefold()
    match_index = -1
    for term in _extract_chat_query_terms(query):
        index = lowered.find(term)
        if index != -1 and (match_index == -1 or index < match_index):
            match_index = index
    if match_index == -1:
        start = 0
    else:
        start = max(0, match_index - CHAT_CONTEXT_PREFIX_CHARS)
    end = min(len(text), start + CHAT_SEARCH_CONTEXT_MAX_CHARS)
    if end == len(text):
        start = max(0, end - CHAT_SEARCH_CONTEXT_MAX_CHARS)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = f"... {excerpt}"
    if end < len(text):
        excerpt = f"{excerpt} ..."
    return excerpt, True


def compact_chat_search_contexts(contexts: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    compacted = []
    for context in contexts:
        content, truncated = compact_chat_context_content(str(context.get("content") or ""), query)
        item = dict(context)
        item["content"] = content
        if truncated:
            item["content_truncated"] = True
            item["source_content_chars"] = len(str(context.get("content") or ""))
        compacted.append(item)
    return compacted


def _extract_chat_query_terms(query: str) -> list[str]:
    terms = []
    for term in re.findall(r"[\w\u4e00-\u9fff']+", query.casefold()):
        if len(term) >= 3 or re.search(r"[\u4e00-\u9fff]", term):
            terms.append(term)
    return terms
