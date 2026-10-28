"""Synthetic integration test for export mechanics; not a Phase 5 model evaluation."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from scripts.export_tabular_onnx import export_and_validate
from src.api.live import TabularRiskAdapter
from src.features.preprocessing import preprocessor
from src.models.onnx_tabular import OnnxTabularEstimator


def test_export_and_validate_sparse_categorical_model(tmp_path):
    generator = np.random.default_rng(31)
    count = 120
    data = pd.DataFrame({
        "claim_id": [f"SYN-{i:03d}" for i in range(count)],
        "injury_claim": generator.normal(100, 20, count),
        "insured_hobbies": generator.choice([f"h{i}" for i in range(30)], count),
    })
    target = ((data.injury_claim > 105) | data.insured_hobbies.isin(["h1", "h2"])).astype(int)
    columns = ["injury_claim", "insured_hobbies"]
    model = Pipeline([
        ("preprocess", preprocessor(data[columns], scale_numeric=False)),
        ("model", XGBClassifier(n_estimators=12, max_depth=2, n_jobs=1, eval_metric="logloss")),
    ])
    model.fit(data[columns], target)
    assert hasattr(model.named_steps["preprocess"].transform(data[columns]), "tocsr")
    raw = np.clip(model.predict_proba(data[columns])[:, 1], 1e-6, 1 - 1e-6)
    logits = np.log(raw / (1 - raw)).reshape(-1, 1)
    calibrator = LogisticRegression().fit(logits, target)
    bundle_path = tmp_path / "bundle.joblib"
    joblib.dump({"model": model, "calibrator": calibrator,
                 "feature_columns": columns, "thresholds": {"t1": 0.4, "t2": 0.8}}, bundle_path)
    sample_path = tmp_path / "validation.csv"
    data.iloc[80:].to_csv(sample_path, index=False)

    output = tmp_path / "onnx"
    report = export_and_validate(bundle_path, sample_path, output, repeats=2)
    assert report["status"] == "parity_passed"
    assert report["scope"] == "xgboost_estimator_only"
    assert report["sparse_missing_encoded_as_nan"] is True
    assert report["sample_rows"] == 40
    assert report["max_calibrated_score_difference"] <= 1e-4
    assert report["queue_mismatch_count"] == 0
    assert (output / "tabular_xgboost.onnx").is_file()
    assert json.loads((output / "validation.json").read_text())["onnx_sha256"] == report["onnx_sha256"]
    runtime = OnnxTabularEstimator(output, bundle_path)
    actual = runtime.predict_raw(model.named_steps["preprocess"], data.iloc[80:][columns])
    reference = model.predict_proba(data.iloc[80:][columns])[:, 1]
    assert np.max(np.abs(actual - reference)) < 1e-4
    example = data.iloc[90][columns].to_dict()
    native_adapter = TabularRiskAdapter(bundle_path)
    onnx_adapter = TabularRiskAdapter(bundle_path, onnx_dir=output)
    assert abs(native_adapter.predict(example)["score"] - onnx_adapter.predict(example)["score"]) < 1e-4
    assert native_adapter.predict(example)["priority"] == onnx_adapter.predict(example)["priority"]

    # Refuse a different fitted preprocessor/model bundle even when its filename matches.
    replaced = tmp_path / "other.joblib"
    joblib.dump({"model": model}, replaced)
    with pytest.raises(ValueError, match="hashes"):
        OnnxTabularEstimator(output, replaced)
