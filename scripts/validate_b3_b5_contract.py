"""Validate a Phase 5 predictions file (and optional evidence manifest) against the B3-B5 contract.

Checks referential integrity and the point-in-time rule (event_time <= scored_at)
so B3-B5 can only be reported when real claim-linked evidence exists. B0-B2 need
only tabular data. See contracts/phase5_b3_b5_data_contract_v1.md.

Run:
    python scripts/validate_b3_b5_contract.py <predictions.csv> [--evidence <manifest.csv>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STAGE_REQUIREMENTS = {
    "B0": set(), "B1": set(), "B2": set(),
    "B3": {"document"},
    "B4": {"document", "image"},
    "B5": {"document", "image", "entity_edge"},
}


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def validate(predictions: Path, evidence: Path | None) -> dict:
    errors: list[str] = []
    frame = _read(predictions)
    for column in ("claim_id", "fraud_label"):
        if column not in frame:
            return {"verdict": "FAIL", "errors": [f"Missing required column: {column}"], "stages": {}}
    if frame.claim_id.isna().any() or not frame.claim_id.is_unique:
        errors.append("claim_id must be unique and non-null")
    labels = frame.fraud_label.to_numpy()
    if not set(np.unique(labels)).issubset({0, 1}) or len(np.unique(labels)) != 2:
        errors.append("fraud_label must contain both classes 0 and 1")

    claim_ids = set(frame.claim_id.astype(str))

    # Which stages are actually scored (column present and not all empty)?
    scored = {}
    for stage in STAGE_REQUIREMENTS:
        column = f"{stage}_score"
        if column in frame and not frame[column].isna().all():
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.isna().any():
                errors.append(f"{column} is partially missing; every scored stage must score the same claims")
            elif not np.isfinite(values.to_numpy()).all():
                errors.append(f"{column} contains non-finite scores")
            scored[stage] = True
        else:
            scored[stage] = False

    # Evidence manifest (optional): referential integrity + point-in-time.
    by_claim: dict[str, set[str]] = {}
    leakage_rows = 0
    if evidence is not None:
        ev = _read(evidence)
        required_cols = {"claim_id", "modality", "evidence_id", "event_time", "scored_at"}
        missing = sorted(required_cols - set(ev.columns))
        if missing:
            errors.append(f"Evidence manifest missing columns: {missing}")
        else:
            orphan = set(ev.claim_id.astype(str)) - claim_ids
            if orphan:
                errors.append(f"Evidence references {len(orphan)} claim_id not in predictions (e.g. {sorted(orphan)[:3]})")
            event = pd.to_datetime(ev.event_time, utc=True, errors="coerce")
            scored_at = pd.to_datetime(ev.scored_at, utc=True, errors="coerce")
            if event.isna().any() or scored_at.isna().any():
                errors.append("Unparseable event_time or scored_at in evidence manifest")
            leakage_rows = int((event > scored_at).sum())
            valid = ev[(event <= scored_at).fillna(False)]
            for cid, group in valid.groupby(valid.claim_id.astype(str)):
                by_claim[cid] = set(group.modality.astype(str))

    # Per-stage verdict.
    stages = {}
    for stage, needs in STAGE_REQUIREMENTS.items():
        if not scored.get(stage):
            stages[stage] = "not_scored"
            continue
        if not needs:
            stages[stage] = "evaluable"
            continue
        if evidence is None:
            stages[stage] = "blocked_no_evidence_manifest"
            continue
        missing_claims = [cid for cid in claim_ids if not needs.issubset(by_claim.get(cid, set()))]
        if leakage_rows:
            stages[stage] = "leakage_future_dated_evidence"
        elif missing_claims:
            stages[stage] = f"blocked_missing_evidence_for_{len(missing_claims)}_claims"
        else:
            stages[stage] = "evaluable"

    bad = any(s.startswith(("blocked", "leakage")) for s in stages.values())
    verdict = "FAIL" if errors else ("BLOCKED" if bad else "PASS")
    return {
        "verdict": verdict,
        "errors": errors,
        "rows": int(len(frame)),
        "positives": int((labels == 1).sum()),
        "leakage_rows": leakage_rows,
        "stages": stages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--evidence", type=Path, default=None)
    args = parser.parse_args()
    report = validate(args.predictions, args.evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
