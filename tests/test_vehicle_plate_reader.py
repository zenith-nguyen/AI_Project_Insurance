from pathlib import Path

from src.document.schema import BoundingBox, OCRToken
from src.image.plate import VehiclePlateReader, looks_like_vietnamese_plate, normalize_plate


def test_plate_normalization_and_vietnamese_pattern():
    assert normalize_plate("51A-123.45") == "51A12345"
    assert looks_like_vietnamese_plate("51A-123.45") is True
    assert looks_like_vietnamese_plate("TOTAL 12345") is False


def test_reader_combines_two_line_plate_and_keeps_bbox():
    def tokens(_: Path):
        return [
            OCRToken("51A", 0.94, BoundingBox(10, 10, 50, 28)),
            OCRToken("123.45", 0.88, BoundingBox(8, 30, 62, 50)),
            OCRToken("XE", 0.99, BoundingBox(70, 10, 90, 30)),
        ]

    readings = VehiclePlateReader(tokens).predict("fixture.png")
    assert readings[0]["normalized_value"] == "51A12345"
    assert readings[0]["confidence"] == 0.88
    assert readings[0]["bbox"] == {"x1": 8, "y1": 10, "x2": 62, "y2": 50}


def test_reader_rejects_low_confidence_and_arbitrary_numbers():
    reader = VehiclePlateReader(lambda _: [
        OCRToken("51A-123.45", 0.3), OCRToken("16.800.000", 0.99),
    ])
    assert reader.predict("fixture.png") == []
