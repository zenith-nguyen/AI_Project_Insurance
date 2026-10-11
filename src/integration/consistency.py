"""Explainable claim-to-document consistency checks."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Iterable

from src.document.schema import ExtractedField


@dataclass(frozen=True)
class ConsistencyCheck:
    claim_id: str
    check_name: str
    status: str
    observed_value: Any
    reference_value: Any
    difference: float | None
    reason_code: str
    evidence_document_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find(fields: Iterable[ExtractedField], name: str) -> ExtractedField | None:
    candidates = [field for field in fields if field.field_name == name]
    return max(candidates, key=lambda field: field.confidence, default=None)


def check_amount(claim_id: str, claim_amount: float | None, fields: list[ExtractedField], document_id: str, tolerance_ratio: float = 0.05) -> ConsistencyCheck:
    field = _find(fields, "total_amount")
    if claim_amount is None or field is None or field.normalized_value is None:
        return ConsistencyCheck(claim_id, "invoice_total_vs_claim_amount", "unknown", field.normalized_value if field else None, claim_amount, None, "missing_field", (document_id,))
    if field.confidence < 0.5:
        return ConsistencyCheck(claim_id, "invoice_total_vs_claim_amount", "unknown", field.normalized_value, claim_amount, None, "low_confidence", (document_id,))
    observed = float(field.normalized_value)
    difference = observed - float(claim_amount)
    ratio = abs(difference) / max(abs(float(claim_amount)), 1.0)
    return ConsistencyCheck(claim_id, "invoice_total_vs_claim_amount", "pass" if ratio <= tolerance_ratio else "fail", observed, claim_amount, difference, "within_tolerance" if ratio <= tolerance_ratio else "amount_mismatch", (document_id,))


def check_plate(claim_id: str, claim_plate: str | None, fields: list[ExtractedField], document_id: str) -> ConsistencyCheck:
    field = _find(fields, "plate_number")
    normalize = lambda value: "".join(char for char in str(value).upper() if char.isalnum())
    if not claim_plate or field is None or field.normalized_value is None:
        return ConsistencyCheck(claim_id, "document_plate_vs_claim_vehicle", "unknown", field.normalized_value if field else None, claim_plate, None, "missing_field", (document_id,))
    matched = normalize(field.normalized_value) == normalize(claim_plate)
    return ConsistencyCheck(claim_id, "document_plate_vs_claim_vehicle", "pass" if matched else "fail", field.normalized_value, claim_plate, None, "match" if matched else "plate_mismatch", (document_id,))


def check_document_date(claim_id: str, incident_date: str | date | None, fields: list[ExtractedField], document_id: str, max_days_after: int = 90) -> ConsistencyCheck:
    field = _find(fields, "document_date")
    if incident_date is None or field is None or field.normalized_value is None:
        return ConsistencyCheck(claim_id, "document_date_vs_incident_date", "unknown", field.normalized_value if field else None, incident_date, None, "missing_field", (document_id,))
    incident = datetime.fromisoformat(str(incident_date)).date()
    observed = datetime.fromisoformat(str(field.normalized_value)).date()
    days = (observed - incident).days
    passed = 0 <= days <= max_days_after
    return ConsistencyCheck(claim_id, "document_date_vs_incident_date", "pass" if passed else "fail", observed.isoformat(), incident.isoformat(), float(days), "within_window" if passed else "date_outside_window", (document_id,))
