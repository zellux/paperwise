from difflib import SequenceMatcher
import re


def strip_nul(value: str) -> str:
    return str(value).replace("\x00", "")


def fit_preview_text(text: str, *, max_chars: int) -> str:
    cleaned = strip_nul(str(text or "")).strip()
    if max_chars <= 0:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    separator = "\n\n...\n\n"
    if len(separator) >= max_chars:
        return cleaned[:max_chars]
    head_len = (max_chars - len(separator)) // 2
    tail_len = max_chars - len(separator) - head_len
    return f"{cleaned[:head_len]}{separator}{cleaned[-tail_len:]}"


def select_pdf_page_numbers(*, page_count: int, max_pages: int) -> list[int]:
    if page_count <= 0 or max_pages <= 0:
        return []
    if page_count <= max_pages:
        return list(range(1, page_count + 1))
    if max_pages == 1:
        return [1]
    if max_pages == 2:
        return [1, page_count]

    selected = [1, 2, page_count]
    if max_pages == 3:
        return selected

    remaining_slots = max_pages - len(selected)
    middle_start = 3
    middle_end = page_count - 1
    if remaining_slots <= 0 or middle_start >= middle_end:
        return selected[:max_pages]

    span = middle_end - middle_start
    inserts: list[int] = []
    for index in range(remaining_slots):
        page_number = middle_start + round((index + 1) * span / (remaining_slots + 1))
        inserts.append(page_number)

    return sorted(set(selected + inserts))


def is_high_quality_extracted_text(text: str) -> bool:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) < 900:
        return False
    letters = sum(ch.isalpha() for ch in cleaned)
    if letters < 400:
        return False
    ratio = letters / max(len(cleaned), 1)
    return ratio >= 0.45


def normalized_text_similarity(left: str, right: str) -> float:
    normalized_left = re.sub(r"[^a-z0-9]+", " ", str(left or "").lower()).strip()
    normalized_right = re.sub(r"[^a-z0-9]+", " ", str(right or "").lower()).strip()
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(a=normalized_left, b=normalized_right).ratio()


def is_good_local_ocr_text(candidate: str, baseline: str) -> bool:
    normalized_candidate = " ".join(str(candidate or "").split())
    if not normalized_candidate:
        return False
    if is_high_quality_extracted_text(normalized_candidate):
        return True

    candidate_letters = sum(ch.isalpha() for ch in normalized_candidate)
    candidate_ratio = candidate_letters / max(len(normalized_candidate), 1)
    normalized_baseline = " ".join(str(baseline or "").split())
    baseline_len = len(normalized_baseline)
    candidate_len = len(normalized_candidate)
    if normalized_baseline:
        baseline_ratio = normalized_text_similarity(normalized_candidate, normalized_baseline)
        min_len = min(candidate_len, baseline_len)
        max_len = max(candidate_len, baseline_len)
        if baseline_ratio >= 0.88 and min_len >= 180 and max_len <= max(1200, min_len + 250):
            return candidate_ratio >= 0.35
    return candidate_len >= max(300, int(baseline_len * 1.5)) and candidate_ratio >= 0.35
