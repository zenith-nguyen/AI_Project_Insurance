"""Score new claim rows for a human review workflow."""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.common import ROOT
from src.features.preprocessing import features


def score(input_file: Path, output_file: Path, bundle_file: Path = ROOT / "artifacts/models/tabular_v1/bundle.joblib") -> pd.DataFrame:
    if input_file.suffix.lower() == ".parquet":
        frame = pd.read_parquet(input_file)
    elif input_file.suffix.lower() == ".csv":
        frame = pd.read_csv(input_file)
    else:
        raise ValueError("Input must be .parquet or .csv")
    if "claim_id" not in frame or frame.claim_id.isna().any() or not frame.claim_id.is_unique:
        raise ValueError("Input requires unique non-null claim_id values")
    bundle = joblib.load(bundle_file)
    x = features(frame)
    expected = bundle["feature_columns"]
    missing = sorted(set(expected) - set(x.columns))
    if missing:
        raise ValueError(f"Missing model feature columns: {missing}")
    raw = np.clip(bundle["model"].predict_proba(x[expected])[:, 1], 1e-6, 1 - 1e-6)
    probability = bundle["calibrator"].predict_proba(np.log(raw / (1 - raw)).reshape(-1, 1))[:, 1]
    thresholds = bundle["thresholds"]
    actions = np.where(probability >= thresholds["t2"], "SIU_review", np.where(probability >= thresholds["t1"], "manual_review", "straight_through_candidate"))
    result = pd.DataFrame({"claim_id": frame.claim_id, "fraud_risk_score": probability, "suggested_queue": actions})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(score(args.input, args.output).head().to_string(index=False))
