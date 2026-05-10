from paperwise.application.services.taxonomy_stats import sort_stat_rows


def test_sort_stat_rows_sorts_text_fields_case_insensitively() -> None:
    rows = [
        {"tag": "zeta", "document_count": 1},
        {"tag": "Alpha", "document_count": 2},
    ]

    assert sort_stat_rows(rows, sort_by="tag", sort_dir="asc") == [
        {"tag": "Alpha", "document_count": 2},
        {"tag": "zeta", "document_count": 1},
    ]


def test_sort_stat_rows_sorts_document_counts() -> None:
    rows = [
        {"document_type": "Invoice", "document_count": 1},
        {"document_type": "Statement", "document_count": 3},
    ]

    assert sort_stat_rows(rows, sort_by="document_count", sort_dir="desc") == [
        {"document_type": "Statement", "document_count": 3},
        {"document_type": "Invoice", "document_count": 1},
    ]


def test_sort_stat_rows_ignores_unknown_sort_options() -> None:
    rows = [{"tag": "Tax", "document_count": 1}]

    assert sort_stat_rows(rows, sort_by="unknown", sort_dir="asc") is rows
    assert sort_stat_rows(rows, sort_by="tag", sort_dir="sideways") is rows
