"""Deterministic key-information extraction baseline after OCR."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .schema import BoundingBox, ExtractedField, OCRToken


DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]){2}\d{2,4}\b")
PLATE_RE = re.compile(r"\b\d{2}[A-Z]-?\d{3,5}(?:\.\d{2})?\b", re.IGNORECASE)
DOC_ID_RE = re.compile(
    r"(?:invoice|receipt|document|claim|h[oó]a\s*đ[oơ]n|s[oố])\s*(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9./-]{3,})",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(
    r"(?:(?:total|amount|grand\s+total|t[oổ]ng\s*(?:ti[eề]n|c[oộ]ng))\s*[:：]?\s*)"
    r"(?:VND|VNĐ|USD|\$)?\s*([0-9][0-9.,\s]{2,})(?:\s*(?:VND|VNĐ|USD|đ))?",
    re.IGNORECASE,
)


def _normalize_date(value: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _normalize_amount(value: str) -> float | None:
    compact = re.sub(r"\s", "", value)
    if "," in compact and "." in compact:
        decimal = "," if compact.rfind(",") > compact.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        compact = compact.replace(thousands, "").replace(decimal, ".")
    elif compact.count(",") == 1 and len(compact.rsplit(",", 1)[1]) <= 2:
        compact = compact.replace(",", ".")
    else:
        compact = compact.replace(",", "").replace(".", "")
    try:
        return float(Decimal(compact))
    except InvalidOperation:
        return None


def _union_box(tokens: list[OCRToken]) -> BoundingBox | None:
    boxes = [token.bbox for token in tokens if token.bbox]
    if not boxes:
        return None
    return BoundingBox(
        min(box.x1 for box in boxes), min(box.y1 for box in boxes),
        max(box.x2 for box in boxes), max(box.y2 for box in boxes),
    )


class RuleBasedKIE:
    model_name = "document-rule-kie"
    model_version = "v1"

    def extract(self, tokens: list[OCRToken]) -> list[ExtractedField]:
        text = " ".join(token.text for token in tokens)
        confidence = sum(token.confidence for token in tokens) / len(tokens) if tokens else 0.0
        evidence = tuple(range(len(tokens)))
        bbox = _union_box(tokens)
        fields: list[ExtractedField] = []

        date = DATE_RE.search(text)
        if date:
            normalized = _normalize_date(date.group(0))
            if normalized:
                fields.append(ExtractedField("document_date", date.group(0), normalized, confidence, bbox=bbox, evidence_token_indexes=evidence))
        amount = AMOUNT_RE.search(text)
        if amount:
            normalized_amount = _normalize_amount(amount.group(1))
            if normalized_amount is not None:
                fields.append(ExtractedField("total_amount", amount.group(1).strip(), normalized_amount, confidence, bbox=bbox, evidence_token_indexes=evidence))
        document_id = DOC_ID_RE.search(text)
        if document_id:
            fields.append(ExtractedField("document_number", document_id.group(1), document_id.group(1).upper(), confidence, bbox=bbox, evidence_token_indexes=evidence))
        plate = PLATE_RE.search(text)
        if plate:
            normalized_plate = re.sub(r"[^A-Z0-9]", "", plate.group(0).upper())
            fields.append(ExtractedField("plate_number", plate.group(0), normalized_plate, confidence, bbox=bbox, evidence_token_indexes=evidence))
        return fields


class LayoutLMv3KIE:
    """Lazy token-classification adapter for a fine-tuned LayoutLMv3 checkpoint."""

    def __init__(self, checkpoint: str, revision: str = "main") -> None:
        if checkpoint == "microsoft/layoutlmv3-base":
            raise ValueError("Base LayoutLMv3 has no task head; provide a fine-tuned KIE checkpoint.")
        try:
            from transformers import AutoModelForTokenClassification, AutoProcessor
        except ImportError as error:
            raise RuntimeError("LayoutLMv3 requires transformers and torch.") from error
        self.model_name = checkpoint
        self.model_version = revision
        self.processor = AutoProcessor.from_pretrained(checkpoint, revision=revision, apply_ocr=False)
        self.model = AutoModelForTokenClassification.from_pretrained(checkpoint, revision=revision)
