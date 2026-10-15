from src.document.schema import ExtractedField
from src.graph.claim_graph import normalize_entity
from src.integration.consistency import check_amount, check_document_date, check_plate


def field(name, value, confidence=0.9):
    return ExtractedField(name, str(value), value, confidence)


def test_entity_normalization_handles_vietnam_phone_plate_and_accents():
    assert normalize_entity("contact_phone", "+84 909 000 111") == "0909000111"
    assert normalize_entity("contact_phone", "0909.000.111") == "0909000111"
    assert normalize_entity("vehicle_plate", "51A-123.45") == "51A12345"
    assert normalize_entity("repair_shop", "Garage Đại Phát") == "GARAGEDAIPHAT"


def test_consistency_returns_unknown_for_malformed_or_low_confidence_fields():
    assert check_amount("C1", 100, [field("total_amount", "not-a-number")], "D1").reason_code == "invalid_amount"
    assert check_document_date("C1", "2026-10-15", [field("document_date", "15/10/2026")], "D1").reason_code == "invalid_date"
    assert check_plate("C1", "51A-123.45", [field("plate_number", "51A12345", 0.2)], "D1").reason_code == "low_confidence"
