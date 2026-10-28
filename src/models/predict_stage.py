"""Score claims at a named checkpoint; outputs are research queue candidates."""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.common import ROOT, config
from src.features.preprocessing import features
from src.models.train_stages import _platt_input


def score(stage: str, input_file: Path, output_file: Path) -> pd.DataFrame:
    allowed = config("configs/stages.yaml")
    if stage not in allowed:
        raise ValueError(f"Choose a stage from {list(allowed)}")
    if input_file.suffix.lower() == ".parquet":
        frame = pd.read_parquet(input_file)
    elif input_file.suffix.lower() == ".csv":
        frame = pd.read_csv(input_file)
    else:
        raise ValueError("Input must be .parquet or .csv")
    if "claim_id" not in frame or frame.claim_id.isna().any() or not frame.claim_id.is_unique:
        raise ValueError("Input needs unique non-null claim_id values")
    bundle = joblib.load(ROOT / "artifacts/models" / f"{stage}_v1/bundle.joblib")
    x = features(frame)
    columns = bundle["feature_columns"]
    missing = sorted(set(columns) - set(x.columns))
    if missing:
        raise ValueError(f"Missing features at {stage}: {missing}")
    raw = bundle["model"].predict_proba(x[columns])[:, 1]
    probabilities = bundle["calibrator"].predict_proba(_platt_input(raw))[:, 1]
    thresholds = bundle["thresholds"]
    queues = np.where(probabilities >= thresholds["t2"], "SIU_review_candidate", np.where(probabilities >= thresholds["t1"], "manual_review_candidate", "low_risk_candidate"))
    output = pd.DataFrame({"claim_id": frame.claim_id, "checkpoint": stage, "research_score": probabilities, "queue_candidate": queues})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_file, index=False)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=list(config("configs/stages.yaml")))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(score(args.stage, args.input, args.output).head().to_string(index=False))
