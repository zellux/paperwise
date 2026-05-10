from paperwise.application.services.taxonomy import resolve_existing_name, resolve_tags


def test_resolve_existing_name_defaults_to_exact_matching() -> None:
    resolved, created = resolve_existing_name(
        "Credit Reports",
        ["Credit Report"],
        fallback="Unknown",
    )

    assert resolved == "Credit Reports"
    assert created is True


def test_resolve_existing_name_supports_fuzzy_matching() -> None:
    resolved, created = resolve_existing_name(
        "Credit Reports",
        ["Credit Report"],
        fallback="Unknown",
        fuzzy_threshold=0.9,
    )

    assert resolved == "Credit Report"
    assert created is False


def test_resolve_tags_supports_fuzzy_matching() -> None:
    resolved, created = resolve_tags(
        ["Credit Reports", "identity"],
        ["Credit Report"],
        fuzzy_threshold=0.9,
    )

    assert resolved == ["Credit Report", "Identity"]
    assert created == ["Identity"]
