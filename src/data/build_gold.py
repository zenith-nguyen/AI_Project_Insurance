"""Freeze stratified splits; all learned preprocessing belongs downstream."""
from __future__ import annotations

import json
from pathlib import Path

from sklearn.model_selection import train_test_split

from src.data.common import ROOT, config, sha256, utc_now, write_json
from src.data.validate_silver import DEFAULT_DIR, validate


def build() -> Path:
    params = config("params.yaml")
    spec = params["gold"]
    ratios = [spec["train_size"], spec["val_size"], spec["test_size"]]
    if any(value <= 0 for value in ratios) or abs(sum(ratios) - 1) > 1e-9:
        raise ValueError("Gold split ratios must be positive and sum to one")
    destination = ROOT / "data/gold" / spec["version"]
    if destination.exists():
        raise FileExistsError(f"Frozen Gold version already exists: {destination}")
    source = validate(DEFAULT_DIR)
    test_count = round(len(source) * spec["test_size"])
    val_count = round(len(source) * spec["val_size"])
    train_val, test = train_test_split(source, test_size=test_count, stratify=source.fraud_label, random_state=params["seed"])
    train, val = train_test_split(train_val, test_size=val_count, stratify=train_val.fraud_label, random_state=params["seed"])
    splits = {"train": train, "val": val, "test": test}
    ids = {name: set(split.claim_id) for name, split in splits.items()}
    if ids["train"] & ids["val"] or ids["train"] & ids["test"] or ids["val"] & ids["test"]:
        raise AssertionError("claim_id overlap between Gold splits")
    destination.mkdir(parents=True)
    manifest = {"version": spec["version"], "created_at_utc": utc_now(), "source_silver_sha256": sha256(DEFAULT_DIR / "claims_silver_v1.parquet"), "seed": params["seed"], "ratios": dict(zip(splits, ratios)), "splits": {}}
    for name, split in splits.items():
        file = destination / f"{name}.parquet"
        split.to_parquet(file, index=False)
        manifest["splits"][name] = {"rows": len(split), "label_counts": {str(k): int(v) for k, v in split.fraud_label.value_counts().items()}, "sha256": sha256(file)}
    write_json(destination / "manifest.json", manifest)
    return destination


if __name__ == "__main__":
    print(build())
