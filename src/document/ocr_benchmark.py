"""Evaluation contract for a private Vietnamese document OCR benchmark."""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .metrics import edit_distance


REQUIRED_MANIFEST_FIELDS = {
    "sample_id",
    "split",
    "image_path",
    "image_sha256",
    "document_type",
    "annotation_status",
    "consent_or_legal_basis",
    "pii_treatment",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    """Apply the locked v1 policy while preserving Vietnamese diacritics."""
    value = unicodedata.normalize("NFC", str(value)).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON on line {line_number} of {path}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"Line {line_number} of {path} must contain a JSON object")
        rows.append(payload)
    return rows


def _reference_text(row: dict[str, Any], manifest_dir: Path) -> str:
    inline = row.get("reference_text")
    relative_path = row.get("reference_text_path")
    if inline is not None and relative_path:
        raise ValueError(f"{row.get('sample_id')}: use reference_text or reference_text_path, not both")
    if inline is not None:
        return str(inline)
    if relative_path:
        path = (manifest_dir / str(relative_path)).resolve()
        if not path.is_relative_to(manifest_dir.resolve()):
            raise ValueError(f"{row.get('sample_id')}: reference_text_path escapes the dataset directory")
        return path.read_text(encoding="utf-8-sig")
    raise ValueError(f"{row.get('sample_id')}: missing reference_text or reference_text_path")


def load_ground_truth(
    manifest_path: Path,
    *,
    require_files: bool = True,
    allowed_splits: Iterable[str] = ("validation",),
) -> list[dict[str, Any]]:
    """Load and validate adjudicated benchmark rows without exposing them in reports."""
    manifest_path = Path(manifest_path).resolve()
    manifest_dir = manifest_path.parent
    allowed = set(allowed_splits)
    rows = _read_jsonl(manifest_path)
    if not rows:
        raise ValueError("OCR benchmark manifest is empty")

    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, source in enumerate(rows, start=1):
        missing = REQUIRED_MANIFEST_FIELDS - source.keys()
        if missing:
            raise ValueError(f"Manifest row {index} is missing fields: {sorted(missing)}")
        row = dict(source)
        sample_id = str(row["sample_id"]).strip()
        if not sample_id or sample_id in seen_ids:
            raise ValueError(f"Duplicate or empty sample_id: {sample_id!r}")
        seen_ids.add(sample_id)
        if row["split"] not in allowed:
            raise ValueError(f"{sample_id}: split {row['split']!r} is not allowed for this evaluation")
        if row["annotation_status"] != "adjudicated":
            raise ValueError(f"{sample_id}: annotation_status must be 'adjudicated'")
        if not str(row["consent_or_legal_basis"]).strip():
            raise ValueError(f"{sample_id}: consent_or_legal_basis is required")
        if row["pii_treatment"] not in {"synthetic", "redacted", "controlled_private"}:
            raise ValueError(f"{sample_id}: unsupported pii_treatment")
        expected_hash = str(row["image_sha256"]).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError(f"{sample_id}: image_sha256 must contain 64 hexadecimal characters")
        if expected_hash in seen_hashes:
            raise ValueError(f"{sample_id}: duplicate image content in the evaluation split")
        seen_hashes.add(expected_hash)
        image_path = (manifest_dir / str(row["image_path"])).resolve()
        if not image_path.is_relative_to(manifest_dir):
            raise ValueError(f"{sample_id}: image_path escapes the dataset directory")
        if require_files:
            if not image_path.is_file():
                raise FileNotFoundError(f"{sample_id}: image does not exist: {image_path}")
            actual_hash = sha256_file(image_path)
            if actual_hash != expected_hash:
                raise ValueError(f"{sample_id}: image SHA-256 does not match the manifest")
        row["sample_id"] = sample_id
        row["resolved_image_path"] = str(image_path)
        row["reference_text_normalized"] = normalize_text(_reference_text(row, manifest_dir))
        validated.append(row)
    return validated


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(Path(path)):
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id or sample_id in predictions:
            raise ValueError(f"Duplicate or empty prediction sample_id: {sample_id!r}")
        if "predicted_text" not in row:
            raise ValueError(f"{sample_id}: predicted_text is required")
        latency = float(row.get("latency_seconds", 0.0))
        if latency < 0:
            raise ValueError(f"{sample_id}: latency_seconds cannot be negative")
        predictions[sample_id] = {
            **row,
            "predicted_text_normalized": normalize_text(row["predicted_text"]),
            "latency_seconds": latency,
        }
    return predictions


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _strip_diacritics(value: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFD", value) if not unicodedata.combining(character))


def _aggregate(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    char_edits = sum(edit_distance(list(reference), list(prediction)) for reference, prediction in pairs)
    char_count = sum(len(reference) for reference, _ in pairs)
    word_edits = sum(edit_distance(reference.split(), prediction.split()) for reference, prediction in pairs)
    word_count = sum(len(reference.split()) for reference, _ in pairs)
    exact = sum(reference == prediction for reference, prediction in pairs)
    return {
        "pages": len(pairs),
        "cer": char_edits / char_count if char_count else 0.0,
        "wer": word_edits / word_count if word_count else 0.0,
        "exact_match_rate": exact / len(pairs) if pairs else 0.0,
        "character_edits": char_edits,
        "reference_characters": char_count,
    }


def evaluate_ocr(
    ground_truth: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    *,
    minimum_pages: int = 50,
) -> dict[str, Any]:
    expected_ids = {row["sample_id"] for row in ground_truth}
    missing = sorted(expected_ids - predictions.keys())
    unexpected = sorted(predictions.keys() - expected_ids)
    if missing or unexpected:
        raise ValueError(f"Prediction coverage mismatch; missing={missing}, unexpected={unexpected}")

    overall_pairs: list[tuple[str, str]] = []
    by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)
    latencies: list[float] = []
    accent_only_pages = 0
    empty_prediction_pages = 0
    page_results: list[dict[str, Any]] = []
    for row in ground_truth:
        prediction = predictions[row["sample_id"]]
        reference_text = row["reference_text_normalized"]
        predicted_text = prediction["predicted_text_normalized"]
        pair = (reference_text, predicted_text)
        overall_pairs.append(pair)
        by_type[str(row["document_type"])].append(pair)
        latencies.append(prediction["latency_seconds"])
        if not predicted_text:
            empty_prediction_pages += 1
        if reference_text != predicted_text and _strip_diacritics(reference_text) == _strip_diacritics(predicted_text):
            accent_only_pages += 1
        page_metric = _aggregate([pair])
        page_results.append({
            "sample_id": row["sample_id"],
            "document_type": row["document_type"],
            "cer": page_metric["cer"],
            "wer": page_metric["wer"],
            "exact_match": reference_text == predicted_text,
            "latency_seconds": prediction["latency_seconds"],
        })

    overall = _aggregate(overall_pairs)
    return {
        "schema_version": "vietnamese_ocr_benchmark_v1",
        "normalization_policy": "unicode_nfc_whitespace_v1_case_sensitive_diacritics_preserved",
        "gate": {
            "minimum_pages": minimum_pages,
            "observed_pages": len(ground_truth),
            "enough_pages_for_domain_claim": len(ground_truth) >= minimum_pages,
            "passed": len(ground_truth) >= minimum_pages,
            "meaning": "PASS permits reporting domain metrics; it does not certify production readiness.",
        },
        "overall": overall,
        "latency_seconds": {
            "mean": statistics.fmean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0,
            "p95": _percentile(latencies, 0.95),
            "total": sum(latencies),
        },
        "error_indicators": {
            "empty_prediction_pages": empty_prediction_pages,
            "accent_only_mismatch_pages": accent_only_pages,
        },
        "by_document_type": {name: _aggregate(pairs) for name, pairs in sorted(by_type.items())},
        "worst_pages": sorted(page_results, key=lambda row: (-row["cer"], row["sample_id"]))[:10],
        "privacy": "Raw reference and predicted text are intentionally excluded from this report.",
    }
