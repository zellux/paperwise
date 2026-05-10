from collections.abc import Iterable
from typing import Any

from paperwise.application.services.taxonomy import to_title_case


def tag_stats_from_metadata(items: Iterable[Any]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for item in items:
        seen: set[str] = set()
        for tag in list(getattr(item, "tags", []) or []):
            cleaned = str(tag).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            display_name_by_key.setdefault(key, to_title_case(cleaned))
            counts[key] = counts.get(key, 0) + 1
    return _sorted_stats(counts, display_name_by_key)


def document_type_stats_from_metadata(items: Iterable[Any]) -> list[tuple[str, int]]:
    return _single_value_stats(items, "document_type", title_case=True)


def correspondent_stats_from_metadata(items: Iterable[Any]) -> list[tuple[str, int]]:
    return _single_value_stats(items, "correspondent", title_case=False)


def sort_stat_rows(
    items: list[dict[str, Any]],
    *,
    sort_by: str | None,
    sort_dir: str | None,
) -> list[dict[str, Any]]:
    field = str(sort_by or "").strip()
    direction = str(sort_dir or "").strip().lower()
    if direction not in {"asc", "desc"}:
        return items
    if field not in {"tag", "document_type", "document_count"}:
        return items
    return sorted(
        items,
        key=lambda item: (
            item.get(field, "") if field == "document_count" else str(item.get(field, "")).casefold()
        ),
        reverse=direction == "desc",
    )


def _single_value_stats(
    items: Iterable[Any],
    attr_name: str,
    *,
    title_case: bool,
) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for item in items:
        cleaned = str(getattr(item, attr_name, "")).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        display_name_by_key.setdefault(key, to_title_case(cleaned) if title_case else cleaned)
        counts[key] = counts.get(key, 0) + 1
    return _sorted_stats(counts, display_name_by_key)


def _sorted_stats(
    counts: dict[str, int],
    display_name_by_key: dict[str, str],
) -> list[tuple[str, int]]:
    return sorted(
        [(display_name_by_key[key], count) for key, count in counts.items()],
        key=lambda item: (-item[1], item[0].casefold()),
    )
