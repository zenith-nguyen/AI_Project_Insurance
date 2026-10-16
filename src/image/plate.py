"""Conservative Vietnamese vehicle-plate reading from local OCR tokens.

This module does not claim that a plate is present merely because the claim
form contains one.  It only returns a reading when text visible in the image
matches a Vietnamese plate pattern and clears a confidence threshold.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from src.document.schema import BoundingBox, OCRToken


_NON_ALNUM = re.compile(r"[^0-9A-Z]")
# Civil and common commercial formats after punctuation is removed.  The
# intentionally broad suffix supports both older 4-digit and current 5-digit
# serials while requiring a province prefix and a letter series.
_PLATE = re.compile(r"^(?:[1-9][0-9])[A-Z]{1,2}[0-9]{4,5}$")


def normalize_plate(value: str) -> str:
    """Normalize OCR text without silently changing ambiguous characters."""
    return _NON_ALNUM.sub("", value.upper())


def looks_like_vietnamese_plate(value: str) -> bool:
    return bool(_PLATE.fullmatch(normalize_plate(value)))


def _union(boxes: Iterable[BoundingBox | None]) -> BoundingBox | None:
    present = [box for box in boxes if box is not None]
    if not present:
        return None
    return BoundingBox(
        min(box.x1 for box in present), min(box.y1 for box in present),
        max(box.x2 for box in present), max(box.y2 for box in present),
    )


@dataclass(frozen=True)
class PlateReading:
    raw_text: str
    normalized_value: str
    confidence: float
    bbox: BoundingBox | None
    method: str = "paddleocr_plate_pattern_v1"

    def to_dict(self) -> dict:
        return asdict(self)


class VehiclePlateReader:
    """Extract high-confidence plate-like strings from an existing OCR engine."""

    model_name = "paddleocr-vehicle-plate-reader"
    model_version = "vi-pattern-v1"

    def __init__(self, token_reader: Callable[[Path], list[OCRToken]], *, min_confidence: float = 0.55) -> None:
        self.token_reader = token_reader
        self.min_confidence = min_confidence

    def predict(self, image: str | Path) -> list[dict]:
        tokens = [token for token in self.token_reader(Path(image)) if token.confidence >= self.min_confidence]
        candidates: list[PlateReading] = []
        # PaddleOCR may return one token (51A-123.45) or split a two-line plate
        # into 51A and 123.45.  Test one to three adjacent OCR tokens.
        for start in range(len(tokens)):
            for width in range(1, 4):
                selected = tokens[start:start + width]
                if len(selected) != width:
                    continue
                raw = " ".join(token.text for token in selected)
                normalized = normalize_plate(raw)
                if not looks_like_vietnamese_plate(normalized):
                    continue
                confidence = min(token.confidence for token in selected)
                candidates.append(PlateReading(raw, normalized, confidence, _union(token.bbox for token in selected)))
        # De-duplicate the same normalized plate, keeping the strongest and
        # most compact OCR grouping.
        strongest: dict[str, PlateReading] = {}
        for candidate in candidates:
            previous = strongest.get(candidate.normalized_value)
            if previous is None or candidate.confidence > previous.confidence:
                strongest[candidate.normalized_value] = candidate
        return [row.to_dict() for row in sorted(strongest.values(), key=lambda item: item.confidence, reverse=True)]
