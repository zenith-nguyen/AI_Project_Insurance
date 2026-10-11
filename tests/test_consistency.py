from src.document.schema import ExtractedField
from src.integration.consistency import check_amount, check_document_date, check_plate


def field(name, value, confidence=0.9):
    return ExtractedField(name, str(value), value, confidence)


def test_amount_check_pass_fail_and_unknown():
    assert check_amount("C1", 100, [field("total_amount", 103)], "D1").status == "pass"
    assert check_amount("C1", 100, [field("total_amount", 120)], "D1").reason_code == "amount_mismatch"
    assert check_amount("C1", 100, [], "D1").status == "unknown"
    assert check_amount("C1", 100, [field("total_amount", 120, 0.2)], "D1").status == "unknown"


def test_plate_and_date_checks():
    assert check_plate("C1", "51A-12345", [field("plate_number", "51A12345")], "D1").status == "pass"
    assert check_document_date("C1", "2026-10-01", [field("document_date", "2026-10-11")], "D1").status == "pass"
    assert check_document_date("C1", "2026-10-11", [field("document_date", "2026-10-01")], "D1").status == "fail"
