from paperwise.application.services.upload_validation import is_supported_upload


def test_requested_lightweight_document_formats_are_supported_uploads() -> None:
    supported = {
        "deck.ppt": "application/vnd.ms-powerpoint",
        "book.xls": "application/vnd.ms-excel",
        "book.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "rows.csv": "text/csv",
        "rows.tsv": "text/tab-separated-values",
        "memo.rtf": "application/rtf",
        "letter.odt": "application/vnd.oasis.opendocument.text",
        "sheet.ods": "application/vnd.oasis.opendocument.spreadsheet",
        "slides.odp": "application/vnd.oasis.opendocument.presentation",
    }

    for filename, content_type in supported.items():
        assert is_supported_upload(filename=filename, content_type=content_type)
