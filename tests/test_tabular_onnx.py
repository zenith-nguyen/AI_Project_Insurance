"""The exported ONNX model must match the joblib bundle's calibrated scores."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.data.common import ROOT
from src.features.preprocessing import features

ART = ROOT / "artifacts/models/tabular_v1"
DATA = ROOT / "data/gold/dataset_v2/test.parquet"

pytestmark = pytest.mark.skipif(
    not (ART / "tabular_xgb.onnx").exists() or not DATA.exists(),
    reason="Run scripts/export_tabular_onnx.py and provide dataset_v2 test first.")


def _reference(bundle, raw):
    engineered = features(raw)
    for column in bundle["feature_columns"]:
        if column not in engineered.columns and column in raw.columns:
            engineered[column] = raw[column].values
    X = engineered[bundle["feature_columns"]]
    prob = np.clip(bundle["model"].predict_proba(X)[:, 1], 1e-6, 1 - 1e-6)
    return bundle["calibrator"].predict_proba(np.log(prob / (1 - prob)).reshape(-1, 1))[:, 1]


def test_onnx_scores_match_joblib_bundle():
    from src.models.onnx_infer import OnnxTabularScorer

    raw = pd.read_parquet(DATA)
    ref = _reference(joblib.load(ART / "bundle.joblib"), raw)
    got = OnnxTabularScorer().score(raw)["fraud_risk_score"].to_numpy()
    assert got.shape == ref.shape
    assert np.max(np.abs(got - ref)) < 1e-5


def test_export_metadata_records_passing_parity():
    meta = json.loads((ART / "tabular_onnx_meta.json").read_text(encoding="utf-8"))
    parity = meta["parity"]
    assert parity["max_abs_diff_final_probability"] < parity["tolerance"]
    assert meta["preprocessed_dim"] > len(meta["feature_columns"])  # one-hot expands columns
