"""Create traceable Silver claims from the named Kaggle Excel workbook."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.data.common import ROOT, sha256, utc_now, write_json


SHEET = "Fraud_Detection_decsion tree"
SOURCE_NAME = "Worksheet in Case Study question 2.xlsx"
SILVER_DIR = ROOT / "data/silver/layerB_claims"


def normalize_name(name: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())).strip("_")


def ingest(source: Path, output_dir: Path = SILVER_DIR) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    output = output_dir / "claims_silver_v1.parquet"
    manifest_path = output_dir / "manifest_v1.json"
    if output.exists() or manifest_path.exists():
        raise FileExistsError("Silver v1 already exists; validate it instead of overwriting it")
    frame = pd.read_excel(source, sheet_name=SHEET)
    if frame.shape != (1000, 39):
        raise ValueError(f"Unexpected source shape: {frame.shape}")
    frame.columns = [normalize_name(column) for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column normalization produced duplicate names")
    if "fraud_reported" not in frame:
        raise ValueError("Missing fraud_reported target")
    frame = frame.replace("?", pd.NA)
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = frame[column].astype("string").str.strip()
    for column in ("policy_bind_date", "incident_date"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="raise")
    frame.insert(0, "claim_id", pd.Series([f"CLM_{i:06d}" for i in range(1, len(frame) + 1)], dtype="string"))
    frame.insert(1, "source_row", range(2, len(frame) + 2))
    frame["fraud_label"] = frame["fraud_reported"].map({"Y": 1, "N": 0}).astype("Int64")
    if frame["fraud_label"].isna().any():
        raise ValueError("Unknown fraud_reported label")
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    manifest = {
        "dataset": "insurance-fraud-detection", "layer": "silver", "version": "v1",
        "created_at_utc": utc_now(), "source_file": source.name, "source_sheet": SHEET,
        "source_sha256": sha256(source), "output_file": output.name,
        "sha256": sha256(output), "rows": len(frame), "columns": len(frame.columns),
        "target": "fraud_label", "target_distribution": {str(k): int(v) for k, v in frame.fraud_label.value_counts().items()},
        "transformations": ["snake_case columns", "? to NA", "categorical strings", "parsed dates", "claim_id", "source_row", "fraud_label"],
    }
    write_json(manifest_path, manifest)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help=f"Path to {SOURCE_NAME}")
    args = parser.parse_args()
    print(ingest(args.source))
