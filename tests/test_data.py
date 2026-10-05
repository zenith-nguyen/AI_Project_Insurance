import json

import pandas as pd

from src.data.common import ROOT, config, sha256
from src.data.validate_silver import validate
from src.features.preprocessing import features


def test_real_silver_manifest_and_schema():
    frame = validate()
    assert frame.claim_id.is_unique
    assert len(frame) == 1000


def test_frozen_gold_has_exact_counts_and_no_claim_overlap():
    folder = ROOT / "data/gold" / config("params.yaml")["gold"]["version"]
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    splits = {name: pd.read_parquet(folder / f"{name}.parquet") for name in ("train", "val", "test")}
    assert {name: len(frame) for name, frame in splits.items()} == {"train": 700, "val": 100, "test": 200}
    assert len(set().union(*(set(frame.claim_id) for frame in splits.values()))) == 1000
    for name in splits:
        assert sha256(folder / f"{name}.parquet") == manifest["splits"][name]["sha256"]


def test_bias_exclusion_policy_removes_named_features():
    folder = ROOT / "data/gold" / config("params.yaml")["gold"]["version"]
    transformed = features(pd.read_parquet(folder / "train.parquet"))
    assert {"insured_hobbies", "insured_zip", "incident_location"}.isdisjoint(transformed.columns)
