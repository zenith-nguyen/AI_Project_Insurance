from __future__ import annotations

from src.document.alignment import align_entity, bio_labels, entity_text


def test_line_level_date_matches_value_without_time() -> None:
    words = ["DOCUMENT NO: 123", "DATE:", "25/12/2018 8:13:39 PM"]
    match = align_entity(words, "date", "25/12/2018")

    assert match is not None
    assert (match.start, match.end, match.method) == (2, 3, "equal_date")


def test_compact_yyyymmdd_matches_receipt_date_format() -> None:
    words = ["DATE:", "04/03/2018 15:41:52"]
    match = align_entity(words, "date", "20180304")

    assert match is not None
    assert (match.start, match.end, match.method) == (1, 2, "equal_date")


def test_total_prefers_matching_amount_near_total_label() -> None:
    words = ["ITEM", "9.00", "TOTAL:", "9.00", "CHANGE", "1.00"]
    match = align_entity(words, "total", "9.00")

    assert match is not None
    assert (match.start, match.end) == (3, 4)
    assert match.method == "exact_compact"


def test_entity_text_flattens_list_representation() -> None:
    assert entity_text(["25/12/2018"]) == "25/12/2018"


def test_bio_labels_are_limited_to_requested_fields() -> None:
    words = ["DATE:", "25/12/2018 8:13 PM", "TOTAL:", "RM 9.00"]
    labels, alignments = bio_labels(
        words,
        {"company": "ignored", "date": "25/12/2018", "total": "9.00"},
        {"date": "DATE", "total": "TOTAL"},
    )

    assert labels == ["O", "B-DATE", "O", "B-TOTAL"]
    assert all(alignments[field] is not None for field in ("date", "total"))
