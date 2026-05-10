def normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def to_title_case(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned

    def looks_like_acronym_token(token: str) -> bool:
        letters = "".join(ch for ch in token if ch.isalpha())
        if not letters or not letters.isalpha():
            return False
        if len(letters) < 2 or len(letters) > 6:
            return False
        vowels = sum(ch in "aeiou" for ch in letters.lower())
        return vowels == 0

    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
            continue
        if looks_like_acronym_token(word):
            words.append(word.upper())
            continue
        if word.islower():
            words.append(word[:1].upper() + word[1:] if word else word)
            continue
        words.append(word)
    return " ".join(words)


def resolve_existing_name(candidate: str, existing: list[str], fallback: str) -> tuple[str, bool]:
    normalized_candidate = normalize_name(candidate)
    if not normalized_candidate:
        return fallback, False
    for name in existing:
        if normalize_name(name) == normalized_candidate:
            return name, False
    return to_title_case(candidate), True


def resolve_tags(candidate_tags: list[str], existing_tags: list[str]) -> tuple[list[str], list[str]]:
    existing_by_norm = {normalize_name(tag): to_title_case(tag) for tag in existing_tags}
    resolved: list[str] = []
    created: list[str] = []
    seen: set[str] = set()
    for tag in candidate_tags:
        normalized = normalize_name(tag)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if normalized in existing_by_norm:
            resolved.append(existing_by_norm[normalized])
            continue
        created_tag = to_title_case(tag)
        resolved.append(created_tag)
        created.append(created_tag)
    return resolved, created
