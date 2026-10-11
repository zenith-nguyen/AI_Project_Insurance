"""Stable, JSON-serializable contracts for document inference."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("Bounding box coordinates are reversed.")

    def as_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass(frozen=True)
class OCRToken:
    text: str
    confidence: float
    bbox: BoundingBox | None = None
    page_number: int = 1

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1.")
        if self.page_number < 1:
            raise ValueError("Page numbers start at 1.")


@dataclass(frozen=True)
class ExtractedField:
    field_name: str
    raw_text: str
    normalized_value: str | float | None
    confidence: float
    page_number: int = 1
    bbox: BoundingBox | None = None
    evidence_token_indexes: tuple[int, ...] = ()
    method: str = "rule"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Field confidence must be between 0 and 1.")


@dataclass
class DocumentResult:
    claim_id: str
    document_id: str
    document_type: str
    document_type_confidence: float
    tokens: list[OCRToken] = field(default_factory=list)
    fields: list[ExtractedField] = field(default_factory=list)
    model_versions: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.document_id.strip():
            raise ValueError("claim_id and document_id are required.")
        if not 0.0 <= self.document_type_confidence <= 1.0:
            raise ValueError("Document type confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
