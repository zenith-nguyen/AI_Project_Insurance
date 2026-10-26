"""Export the tabular XGBoost model to ONNX for CPU inference (Phase 6 backlog item).

The trained bundle is artifacts/models/tabular_v1/bundle.joblib: a sklearn
ColumnTransformer preprocess, an XGBClassifier, and a logistic calibrator.
Only the XGBoost stage is exported to ONNX (the heavy native dependency); the
preprocess stays as a small sklearn ColumnTransformer and the calibrator is a
two-parameter sigmoid stored in metadata, so inference needs only sklearn +
onnxruntime + numpy, not xgboost.

Full-pipeline ONNX (including the string imputer/one-hot) is not emitted because
skl2onnx cannot yet convert a float-NaN SimpleImputer over string columns; that
remains future work.

Run:
    python scripts/export_tabular_onnx.py
Outputs under artifacts/models/tabular_v1/:
    tabular_xgb.onnx, tabular_preprocess.joblib, tabular_onnx_meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.common import ROOT
from src.features.preprocessing import features

BUNDLE = ROOT / "artifacts/models/tabular_v1/bundle.joblib"
OUT_DIR = ROOT / "artifacts/models/tabular_v1"
PARITY_DATA = ROOT / "data/gold/dataset_v2/test.parquet"


def _feature_frame(bundle: dict) -> pd.DataFrame:
    """Build the model's expected feature frame; re-add proxy columns the current
    bias policy drops from features() but that the tabular_v1 bundle was trained on."""
    raw = pd.read_parquet(PARITY_DATA)
    engineered = features(raw)
    for column in bundle["feature_columns"]:
        if column not in engineered.columns and column in raw.columns:
            engineered[column] = raw[column].values
    return engineered[bundle["feature_columns"]]


def _dense(matrix) -> np.ndarray:
    """Densify the preprocessed matrix for ONNX. The training pipeline feeds a
    sparse matrix to XGBoost, so unset one-hot / zero entries are treated as
    MISSING, not as real zeros. onnxruntime takes a dense array, so we restore
    that semantics by mapping 0.0 to NaN (the booster's missing value)."""
    if hasattr(matrix, "toarray"):
        matrix = matrix.toarray()
    dense = np.asarray(matrix, dtype=np.float32)
    dense = np.where(dense == 0.0, np.nan, dense).astype(np.float32)
    return np.ascontiguousarray(dense)


def export() -> dict:
    bundle = joblib.load(BUNDLE)
    pre = bundle["model"].named_steps["preprocess"]
    xgb = bundle["model"].named_steps["model"]
    calibrator = bundle["calibrator"]

    from skl2onnx import convert_sklearn, update_registered_converter
    from skl2onnx.common.data_types import FloatTensorType
    from skl2onnx.common.shape_calculator import calculate_linear_classifier_output_shapes
    from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost
    from xgboost import XGBClassifier

    update_registered_converter(
        XGBClassifier, "XGBoostXGBClassifier",
        calculate_linear_classifier_output_shapes, convert_xgboost,
        options={"nocl": [True, False], "zipmap": [True, False, "columns"]})

    X = _feature_frame(bundle)
    Xp = _dense(pre.transform(X))
    onnx_model = convert_sklearn(
        xgb, initial_types=[("input", FloatTensorType([None, Xp.shape[1]]))],
        options={"zipmap": False}, target_opset={"": 17, "ai.onnx.ml": 3})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = OUT_DIR / "tabular_xgb.onnx"
    onnx_path.write_bytes(onnx_model.SerializeToString())
    joblib.dump(pre, OUT_DIR / "tabular_preprocess.joblib")

    # Parity: ONNX + sigmoid calibrator vs the original joblib pipeline.
    import onnxruntime as ort
    sess = ort.InferenceSession(onnx_path.read_bytes(), providers=["CPUExecutionProvider"])
    onnx_raw = _probability_column(sess.run(None, {"input": Xp}))

    ref = _calibrated(np.clip(bundle["model"].predict_proba(X)[:, 1], 1e-6, 1 - 1e-6), calibrator)
    got = _calibrated(np.clip(onnx_raw, 1e-6, 1 - 1e-6), calibrator)
    max_abs_diff = float(np.max(np.abs(got - ref)))

    meta = {
        "onnx_file": "tabular_xgb.onnx",
        "preprocess_file": "tabular_preprocess.joblib",
        "input_name": "input",
        "preprocessed_dim": int(Xp.shape[1]),
        "feature_columns": bundle["feature_columns"],
        "calibrator": {"coef": float(calibrator.coef_.ravel()[0]),
                       "intercept": float(calibrator.intercept_.ravel()[0]),
                       "applies_to": "logit of clipped onnx probability"},
        "thresholds": bundle["thresholds"],
        "parity": {"rows": int(len(ref)), "max_abs_diff_final_probability": max_abs_diff,
                   "tolerance": 1e-5, "dataset": str(PARITY_DATA.relative_to(ROOT))},
        "note": "Preprocess stays sklearn; only XGBoost is ONNX. Inference needs sklearn+onnxruntime+numpy, not xgboost.",
    }
    (OUT_DIR / "tabular_onnx_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def _probability_column(outputs) -> np.ndarray:
    for out in outputs:
        array = np.asarray(out)
        if array.ndim == 2 and array.shape[1] == 2:
            return array[:, 1]
    raise RuntimeError("ONNX model did not return a 2-column probability output.")


def _calibrated(raw: np.ndarray, calibrator) -> np.ndarray:
    logit = np.log(raw / (1 - raw)).reshape(-1, 1)
    return calibrator.predict_proba(logit)[:, 1]


if __name__ == "__main__":
    result = export()
    print(json.dumps({"preprocessed_dim": result["preprocessed_dim"],
                      "parity_max_abs_diff": result["parity"]["max_abs_diff_final_probability"],
                      "rows": result["parity"]["rows"]}, indent=2))
    print("Saved tabular_xgb.onnx, tabular_preprocess.joblib, tabular_onnx_meta.json under artifacts/models/tabular_v1/")
