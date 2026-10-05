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


def test_feature_selection_split_reconstructs_original_train_and_excludes_test():
    params = config("params.yaml")
    gold_folder = ROOT / "data/gold" / params["gold"]["version"]
    fs_folder = ROOT / "data/gold" / params["feature_selection"]["version"]
    manifest = json.loads((fs_folder / "manifest.json").read_text(encoding="utf-8"))
    original_train = pd.read_parquet(gold_folder / "train.parquet")
    original_test = pd.read_parquet(gold_folder / "test.parquet")
    train_fs = pd.read_parquet(fs_folder / "train_fs.parquet")
    val_fs = pd.read_parquet(fs_folder / "val_fs.parquet")

    assert (len(train_fs), len(val_fs)) == (560, 140)
    assert set(train_fs.claim_id) | set(val_fs.claim_id) == set(original_train.claim_id)
    assert set(train_fs.claim_id).isdisjoint(val_fs.claim_id)
    assert (set(train_fs.claim_id) | set(val_fs.claim_id)).isdisjoint(original_test.claim_id)
    for name in ("train_fs", "val_fs"):
        assert sha256(fs_folder / f"{name}.parquet") == manifest["splits"][name]["sha256"]


def test_bias_exclusion_policy_removes_named_features():
    folder = ROOT / "data/gold" / config("params.yaml")["gold"]["version"]
    frame = pd.read_parquet(folder / "train.parquet")
    transformed = features(frame)
    full_research = features(frame, exclude_biased_features=False)
    assert {"insured_hobbies", "insured_zip", "incident_location"}.isdisjoint(transformed.columns)
    assert "insured_hobbies" in full_research.columns
    assert {"insured_zip", "incident_location"}.isdisjoint(full_research.columns)
