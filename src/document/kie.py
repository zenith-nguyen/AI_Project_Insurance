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

    def extract(self, tokens: list[OCRToken], image=None) -> list[ExtractedField]:
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

    def __init__(self, checkpoint: str, revision: str = "main", device: str | None = None) -> None:
        if checkpoint == "microsoft/layoutlmv3-base":
            raise ValueError("Base LayoutLMv3 has no task head; provide a fine-tuned KIE checkpoint.")
        try:
            import torch
            from transformers import AutoModelForTokenClassification, AutoProcessor
        except ImportError as error:
            raise RuntimeError("LayoutLMv3 requires transformers and torch.") from error
        self.model_name = checkpoint
        self.model_version = revision
        self._torch = torch
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoProcessor.from_pretrained(checkpoint, revision=revision, apply_ocr=False)
        self.model = AutoModelForTokenClassification.from_pretrained(checkpoint, revision=revision).to(self._device)
        self.model.eval()

    @staticmethod
    def _spans(labels: list[str]) -> list[tuple[str, int, int]]:
        spans: list[tuple[str, int, int]] = []
        active_name, active_start = None, None
        for index, label in enumerate(labels + ["O"]):
            prefix, name = label.split("-", 1) if "-" in label else (label, None)
            if active_name is not None and (prefix != "I" or name != active_name):
                spans.append((active_name, active_start, index))
                active_name, active_start = None, None
            if prefix == "B":
                active_name, active_start = name, index
            elif prefix == "I" and active_name is None:
                active_name, active_start = name, index
        return spans

    def extract(self, tokens: list[OCRToken], image=None) -> list[ExtractedField]:
        if image is None or not tokens:
            return []
        from PIL import Image

        with Image.open(image) as opened:
            rgb = opened.convert("RGB")
            width, height = rgb.size
            words = [token.text for token in tokens]
            boxes = []
            for token in tokens:
                box = token.bbox
                if box is None:
                    boxes.append([0, 0, 0, 0])
                else:
                    boxes.append([
                        max(0, min(1000, round(1000 * box.x1 / width))),
                        max(0, min(1000, round(1000 * box.y1 / height))),
                        max(0, min(1000, round(1000 * box.x2 / width))),
                        max(0, min(1000, round(1000 * box.y2 / height))),
                    ])
            encoded = self.processor(
                rgb, words, boxes=boxes, truncation=True, padding="max_length",
                max_length=512, return_tensors="pt",
            )
        word_ids = encoded.word_ids(batch_index=0)
        inputs = {key: value.to(self._device) for key, value in encoded.items()}
        with self._torch.inference_mode():
            probabilities = self.model(**inputs).logits.softmax(dim=-1)[0].cpu()
        token_predictions = probabilities.argmax(dim=-1).tolist()
        id2label = {int(key): value for key, value in self.model.config.id2label.items()}
        word_labels = ["O"] * len(words)
        word_confidence = [0.0] * len(words)
        seen: set[int] = set()
        for token_index, word_id in enumerate(word_ids):
            if word_id is None or word_id in seen or word_id >= len(words):
                continue
            seen.add(word_id)
            label_id = int(token_predictions[token_index])
            word_labels[word_id] = str(id2label[label_id])
            word_confidence[word_id] = float(probabilities[token_index, label_id])

        fields: list[ExtractedField] = []
        for name, start, end in self._spans(word_labels):
            selected = tokens[start:end]
            raw = " ".join(token.text for token in selected)
            if name == "DATE":
                normalized = _normalize_date(raw)
                field_name = "document_date"
            elif name == "TOTAL":
                normalized = _normalize_amount(raw)
                field_name = "total_amount"
            else:
                continue
            confidence = sum(word_confidence[start:end]) / max(end - start, 1)
            fields.append(ExtractedField(
                field_name, raw, normalized, confidence, bbox=_union_box(selected),
                evidence_token_indexes=tuple(range(start, end)), method="layoutlmv3",
            ))
        return fields
