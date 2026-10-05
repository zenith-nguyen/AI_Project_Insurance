"""Create a feature-selection holdout exclusively from the original Gold train split."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.common import ROOT, config, sha256, utc_now, write_json


def build() -> Path:
    params = config("params.yaml")["feature_selection"]
    source_dir = ROOT / "data/gold" / params["source_gold_version"]
    destination = ROOT / "data/gold" / params["version"]
    if destination.exists():
        raise FileExistsError(f"Feature-selection split already exists: {destination}")

    source_manifest_path = source_dir / "manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_train_path = source_dir / "train.parquet"
    spent_test_path = source_dir / "test.parquet"
    if sha256(source_train_path) != source_manifest["splits"]["train"]["sha256"]:
        raise ValueError("Original Gold train hash mismatch")
    if sha256(spent_test_path) != source_manifest["splits"]["test"]["sha256"]:
        raise ValueError("Original frozen test hash mismatch")

    source_train = pd.read_parquet(source_train_path)
    spent_test = pd.read_parquet(spent_test_path)
    val_count = round(len(source_train) * float(params["val_size"]))
    train_fs, val_fs = train_test_split(
        source_train,
        test_size=val_count,
        stratify=source_train["fraud_label"],
        random_state=int(params["seed"]),
    )
    train_ids, val_ids, test_ids = map(set, (train_fs.claim_id, val_fs.claim_id, spent_test.claim_id))
    if train_ids & val_ids or train_ids & test_ids or val_ids & test_ids:
        raise AssertionError("claim_id overlap found between train_fs, val_fs, and original frozen test")
    if train_ids | val_ids != set(source_train.claim_id):
        raise AssertionError("train_fs and val_fs do not reconstruct the original Gold train split")

    destination.mkdir(parents=True)
    split_frames = {"train_fs": train_fs, "val_fs": val_fs}
    manifest = {
        "version": params["version"],
        "created_at_utc": utc_now(),
        "purpose": "feature-policy and feature-selection decisions after the original frozen test was reused",
        "source_gold_version": params["source_gold_version"],
        "source_gold_train_sha256": sha256(source_train_path),
        "original_frozen_test_sha256": sha256(spent_test_path),
        "original_frozen_test_status": "spent for feature-policy comparison as of 2026-10-05; never use it for further feature selection",
        "seed": int(params["seed"]),
        "val_size_within_original_train": float(params["val_size"]),
        "splits": {},
    }
    for name, frame in split_frames.items():
        path = destination / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        manifest["splits"][name] = {
            "rows": len(frame),
            "label_counts": {str(key): int(value) for key, value in frame.fraud_label.value_counts().items()},
            "sha256": sha256(path),
        }
    write_json(destination / "manifest.json", manifest)
    return destination


if __name__ == "__main__":
    print(build())
