"""Export the trained XGBoost component and gate it against the original bundle.

The fitted sklearn preprocessor and Platt calibrator remain in bundle.joblib.
This tool does not turn the whole claim-review system into a standalone ONNX app.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse

from src.features.preprocessing import features
from src.models.onnx_tabular import float32_matrix, positive_probability, sha256


def _read_sample(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Sample must be .csv or .parquet")
    if frame.empty or "claim_id" not in frame or frame.claim_id.isna().any() or not frame.claim_id.is_unique:
        raise ValueError("Sample needs nonempty, unique claim_id values")
    return frame


def _calibrate(raw: np.ndarray, calibrator) -> np.ndarray:
    clipped = np.clip(raw, 1e-6, 1 - 1e-6)
    return calibrator.predict_proba(np.log(clipped / (1 - clipped)).reshape(-1, 1))[:, 1]


def _queues(score: np.ndarray, thresholds: dict) -> np.ndarray:
    return np.where(score >= thresholds["t2"], "SIU", np.where(score >= thresholds["t1"], "SUPPLEMENT", "STP"))


def export_and_validate(bundle_path: Path, sample_path: Path, output_dir: Path, *,
                        max_score_diff: float = 1e-4, repeats: int = 10) -> dict:
    """Write an ONNX model and manifest only when the fixed-sample gate passes."""
    if repeats < 1 or max_score_diff < 0:
        raise ValueError("repeats must be positive and max_score_diff nonnegative")
    from onnxmltools import convert_xgboost
    from onnxmltools.convert.common.data_types import FloatTensorType
    import onnx
    import onnxruntime as ort
    from xgboost import XGBClassifier

    bundle = joblib.load(bundle_path)
    pipeline = bundle["model"]
    estimator = pipeline.named_steps["model"]
    if not isinstance(estimator, XGBClassifier):
        raise ValueError("Only fitted XGBClassifier tabular bundles are supported")
    expected = list(bundle["feature_columns"])
    sample = _read_sample(sample_path)
    x = features(sample, exclude_biased_features=False)
    missing = sorted(set(expected) - set(x.columns))
    if missing:
        raise ValueError(f"Sample missing features: {missing}")
    x = x[expected]
    transformed = pipeline.named_steps["preprocess"].transform(x)
    onnx_input = float32_matrix(transformed)
    native_raw = pipeline.predict_proba(x)[:, 1]
    native_score = _calibrate(native_raw, bundle["calibrator"])

    model = convert_xgboost(estimator, initial_types=[("features", FloatTensorType([None, onnx_input.shape[1]]))])
    onnx.checker.check_model(model)
    session = ort.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    def onnx_raw() -> np.ndarray:
        return positive_probability(session.run(None, {input_name: onnx_input}), len(x))

    converted_raw = onnx_raw()
    converted_score = _calibrate(converted_raw, bundle["calibrator"])
    raw_diff = float(np.max(np.abs(native_raw - converted_raw)))
    score_diff = float(np.max(np.abs(native_score - converted_score)))
    queue_mismatch = int(np.count_nonzero(_queues(native_score, bundle["thresholds"]) !=
                                             _queues(converted_score, bundle["thresholds"])))
    if not np.isfinite(converted_score).all() or score_diff > max_score_diff or queue_mismatch:
        raise ValueError(f"ONNX parity gate failed: max_score_diff={score_diff:.8g}, queue_mismatch={queue_mismatch}")

    # Time equivalent paths, including fitted preprocessing and calibration.
    def native_inference() -> np.ndarray:
        return _calibrate(pipeline.predict_proba(x)[:, 1], bundle["calibrator"])

    def onnx_inference() -> np.ndarray:
        converted = float32_matrix(pipeline.named_steps["preprocess"].transform(x))
        output = positive_probability(session.run(None, {input_name: converted}), len(x))
        return _calibrate(output, bundle["calibrator"])

    native_inference()
    onnx_inference()
    native_ms, onnx_ms = [], []
    for _ in range(repeats):
        start = time.perf_counter()
        native_inference()
        native_ms.append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()
        onnx_inference()
        onnx_ms.append((time.perf_counter() - start) * 1000)

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "tabular_xgboost.onnx"
    with tempfile.NamedTemporaryFile(dir=output_dir, suffix=".onnx", delete=False) as tmp:
        tmp.write(model.SerializeToString())
        temporary = Path(tmp.name)
    temporary.replace(destination)
    report = {
        "status": "parity_passed", "scope": "xgboost_estimator_only",
        "preprocessing": "original_fitted_joblib_pipeline", "calibration": "original_fitted_joblib_calibrator",
        "sample_rows": len(x), "sample_sha256": sha256(sample_path),
        "bundle_sha256": sha256(bundle_path), "onnx_sha256": sha256(destination),
        "transformed_feature_count": int(onnx_input.shape[1]),
        "sparse_missing_encoded_as_nan": bool(sparse.issparse(transformed)),
        "max_raw_difference": raw_diff, "max_calibrated_score_difference": score_diff,
        "max_allowed_score_difference": max_score_diff, "queue_mismatch_count": queue_mismatch,
        "batch_cpu_ms_p95": {"native": float(np.percentile(native_ms, 95)), "onnx": float(np.percentile(onnx_ms, 95))},
        "benchmark_repeats": repeats,
        "limitations": ["No end-to-end ONNX preprocessing or calibration", "No validated live claim-linked B3-B5 evaluation", "Latency is hardware-dependent"],
    }
    (output_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True, help="Locked validation or other non-final-test split")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-score-diff", type=float, default=1e-4)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    report = export_and_validate(args.bundle, args.sample, args.output_dir,
                                 max_score_diff=args.max_score_diff, repeats=args.repeats)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
