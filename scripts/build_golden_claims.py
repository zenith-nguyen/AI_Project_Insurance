"""Build deterministic, de-identified golden claims for end-to-end product tests."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/gold/feature_selection_v1/train_fs.parquet"
OUTPUT = ROOT / "data/golden/claims"


def _json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build() -> list[Path]:
    rows = pd.read_parquet(SOURCE).head(5)
    created: list[Path] = []
    for index, (_, source) in enumerate(rows.iterrows(), start=1):
        claim_id = f"CLM-GOLD-{index:03d}"
        root = OUTPUT / claim_id
        features = {
            key: _json_value(value)
            for key, value in source.items()
            if key not in {"claim_id", "source_row", "fraud_reported", "fraud_label"}
        }
        # Replace source identifiers and direct location fields with synthetic values.
        features["policy_number"] = 900000 + index
        features["insured_zip"] = 700000 + index
        features["incident_location"] = f"Synthetic location {index}"
        plate = f"51G-{index:03d}.88"
        claim_amount = float(features["vehicle_claim"])
        mismatch = index in {1, 3, 5}
        document_total = round(claim_amount * (1.18 if mismatch else 1.02), 2)
        incident_date = str(features["incident_date"])
        scored_at = "2026-10-13T02:00:00Z"

        claim = {
            "schema_version": "1.0",
            "claim_id": claim_id,
            "data_origin": "deidentified_public_research_row",
            "synthetic_identifiers": True,
            "scored_at": scored_at,
            "claim_amount": claim_amount,
            "incident_date": incident_date,
            "plate_number": plate,
            "tabular_features": features,
            "required_evidence": ["claim-intake", "repair-estimate", "vehicle-image-manifest"],
        }
        document = {
            "claim_id": claim_id,
            "document_id": f"DOC-{index:03d}",
            "evidence_id": "repair-estimate",
            "document_type": "repair_estimate",
            "source": "golden_precomputed_fields",
            "fields": [
                {"field_name": "total_amount", "raw_text": str(document_total), "normalized_value": document_total, "confidence": 0.95},
                {"field_name": "document_date", "raw_text": incident_date, "normalized_value": incident_date, "confidence": 0.97},
                {"field_name": "plate_number", "raw_text": plate, "normalized_value": plate, "confidence": 0.96},
            ],
        }
        previous_claim = f"CLM-HISTORY-{index:03d}"
        entity = f"SHOP-SHARED-{(index + 1) // 2:02d}"
        graph = {
            "scored_at": scored_at,
            "known_risky_claims": [previous_claim] if index in {3, 5} else [],
            "nodes": [
                {"id": claim_id, "entity_type": "claim", "available_at": "2026-10-12T00:00:00Z"},
                {"id": previous_claim, "entity_type": "claim", "available_at": "2026-09-01T00:00:00Z"},
                {"id": entity, "entity_type": "repair_shop", "available_at": "2026-01-01T00:00:00Z"},
            ],
            "edges": [
                {"source": claim_id, "target": entity, "relation": "uses_repair_shop", "event_time": "2026-10-12T01:00:00Z"},
                {"source": previous_claim, "target": entity, "relation": "uses_repair_shop", "event_time": "2026-09-01T01:00:00Z"},
            ],
        }
        images = {
            "claim_id": claim_id,
            "data_origin": "synthetic_manifest",
            "images": [{"evidence_id": "vehicle-image-manifest", "filename": None, "status": "placeholder_no_binary"}],
        }
        expected = {
            "claim_id": claim_id,
            "human_review_required": True,
            "required_signal_categories": ["consistency", "relationship"] if mismatch else ["relationship"],
            "amount_check": "fail" if mismatch else "pass",
            "test_scope": "API orchestration and claim_id continuity; image/document inference requires separate binary fixtures.",
        }
        write(root / "claim.json", claim)
        write(root / "documents" / "repair_estimate.json", document)
        write(root / "vehicle_images" / "manifest.json", images)
        write(root / "entities.json", graph)
        write(root / "expected_analysis.json", expected)
        created.append(root)
    return created


if __name__ == "__main__":
    paths = build()
    print(f"Golden claims: {len(paths)}")
    for path in paths:
        print(path.relative_to(ROOT))
