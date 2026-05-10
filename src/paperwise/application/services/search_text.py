import re


def tokenize_search_query(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]{2,}", query)]


def extract_search_snippet(text: str, terms: list[str], *, max_len: int = 240) -> str:
    source = str(text or "")
    if not source.strip():
        return ""
    lowered = source.lower()
    pos = -1
    for term in terms:
        idx = lowered.find(term)
        if idx >= 0:
            pos = idx
            break
    if pos < 0:
        return " ".join(source.split())[:max_len]
    start = max(0, pos - max_len // 3)
    end = min(len(source), start + max_len)
    return " ".join(source[start:end].split())
