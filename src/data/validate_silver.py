"""Validate the actual Silver artifact before downstream work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.data.common import ROOT, sha256


DEFAULT_DIR = ROOT / "data/silver/layerB_claims"
EXPECTED_MISSING = {"property_damage": 360, "police_report_available": 343, "collision_type": 178, "authorities_contacted": 91}


def validate(directory: Path = DEFAULT_DIR) -> pd.DataFrame:
    file = directory / "claims_silver_v1.parquet"
    manifest_file = directory / "manifest_v1.json"
    if not file.exists() or not manifest_file.exists():
        raise FileNotFoundError(f"Silver files required in {directory}: {file.name}, {manifest_file.name}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if sha256(file) != manifest["sha256"]:
        raise ValueError("Silver SHA-256 does not match its manifest")
    frame = pd.read_parquet(file)
    if frame.shape != (1000, 42) or manifest["rows"] != 1000 or manifest["columns"] != 42:
        raise ValueError(f"Unexpected Silver shape: {frame.shape}")
    if not {"claim_id", "source_row", "fraud_reported", "fraud_label"}.issubset(frame.columns):
        raise ValueError("Required trace/target columns missing")
    if frame.claim_id.isna().any() or not frame.claim_id.is_unique:
        raise ValueError("claim_id must be unique and non-null")
    if frame.source_row.isna().any() or not frame.source_row.is_unique:
        raise ValueError("source_row must be unique and non-null")
    counts = {int(k): int(v) for k, v in frame.fraud_label.value_counts().items()}
    if counts != {0: 753, 1: 247}:
        raise ValueError(f"Unexpected label counts: {counts}")
    if (frame.fraud_reported.map({"N": 0, "Y": 1}).astype("Int64") != frame.fraud_label).any():
        raise ValueError("fraud_label disagrees with original label")
    for column, count in EXPECTED_MISSING.items():
        if column not in frame or frame[column].isna().sum() != count:
            raise ValueError(f"Unexpected missing count for {column}")
    if any(frame[column].astype("string").eq("?").any() for column in frame.select_dtypes(include=["object", "string"]).columns):
        raise ValueError("Found unnormalized ? placeholder")
    for column in ("policy_bind_date", "incident_date"):
        if not pd.api.types.is_datetime64_any_dtype(frame[column]):
            raise ValueError(f"{column} must be datetime")
    return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    data = validate(args.directory)
    print(f"Silver valid: {data.shape}, label counts {data.fraud_label.value_counts().to_dict()}")
