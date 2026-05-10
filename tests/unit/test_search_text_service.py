from paperwise.application.services.search_text import extract_search_snippet, tokenize_search_query


def test_tokenize_search_query_keeps_alphanumeric_terms() -> None:
    assert tokenize_search_query("Invoice #A1 for 2026-05") == ["invoice", "a1", "for", "2026", "05"]


def test_extract_search_snippet_centers_first_matching_term() -> None:
    text = "alpha " * 30 + "needle " + "omega " * 30

    snippet = extract_search_snippet(text, ["needle"], max_len=80)

    assert "needle" in snippet
    assert len(snippet) <= 80


def test_extract_search_snippet_falls_back_to_compact_prefix() -> None:
    assert extract_search_snippet("alpha    beta\n gamma", ["missing"], max_len=12) == "alpha beta g"
