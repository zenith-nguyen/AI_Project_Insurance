"""Descriptive, small-sample audit of the locked Phase 5 validation cohort.

Usage: python scripts/fairness_audit_phase5.py --val val_fs.parquet --pred predictions_locked_val.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def audit(val_path: Path, predictions_path: Path) -> dict:
    val = pd.read_parquet(val_path)
    pred = pd.read_csv(predictions_path)
    if not val.claim_id.is_unique or not pred.claim_id.is_unique:
        raise ValueError("claim_id must be unique in both sources")
    if set(val.claim_id) != set(pred.claim_id):
        raise ValueError("Prediction and validation claim IDs do not match")
    frame = val[["claim_id", "fraud_label", "insured_sex", "age"]].merge(
        pred[["claim_id", "fraud_label", "B2_score"]], on="claim_id", validate="one_to_one",
        suffixes=("_val", "_pred"),
    )
    if not (frame.fraud_label_val == frame.fraud_label_pred).all():
        raise ValueError("Labels disagree")
    if frame.B2_score.isna().any():
        raise ValueError("Missing B2 predictions")
    # Stable, label-independent tie break. Top 10% of the WHOLE cohort.
    frame = frame.sort_values(["B2_score", "claim_id"], ascending=[False, True])
    selected = max(1, round(len(frame) * .1))
    frame["selected"] = False
    frame.iloc[:selected, frame.columns.get_loc("selected")] = True
    frame["age_band"] = pd.cut(frame.age, bins=[0, 39, 54, 200], labels=["<=39", "40-54", "55+"])
    groups = {}
    for field in ("insured_sex", "age_band"):
        groups[field] = []
        for group, rows in frame.groupby(field, observed=True, dropna=False):
            positives = int(rows.fraud_label_val.sum())
            selected_rows = rows[rows.selected]
            selected_positives = int(selected_rows.fraud_label_val.sum())
            groups[field].append({
                "group": str(group), "n": len(rows), "positive": positives,
                "selected": len(selected_rows), "selected_positive": selected_positives,
                "selection_rate": len(selected_rows) / len(rows),
                "recall_in_global_top_k": selected_positives / positives if positives else None,
                "precision_in_global_top_k": selected_positives / len(selected_rows) if len(selected_rows) else None,
            })
    return {"cohort": "locked_val_fs", "model": "Phase5_B2", "n": len(frame),
            "global_top_k": selected, "selected_positive": int(frame[frame.selected].fraud_label_val.sum()),
            "groups": groups, "interpretation": "descriptive development validation; not a fairness certification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--val", required=True, type=Path)
    parser.add_argument("--pred", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(args.val, args.pred)
    formatted = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(formatted + "\n", encoding="utf-8")
    else:
        print(formatted)
