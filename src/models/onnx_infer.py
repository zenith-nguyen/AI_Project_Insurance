"""CPU inference for the tabular risk model through ONNX (no xgboost at runtime).

Mirrors src/models/predict.py but runs the XGBoost stage in onnxruntime. Runtime
dependencies are sklearn (preprocess), onnxruntime and numpy; xgboost is only
needed once, to build the artifacts with scripts/export_tabular_onnx.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.common import ROOT
from src.features.preprocessing import features

ARTIFACTS = ROOT / "artifacts/models/tabular_v1"


class OnnxTabularScorer:
    """Score claim rows with the exported ONNX model and sigmoid calibrator."""

    def __init__(self, artifacts_dir: Path = ARTIFACTS):
        import onnxruntime as ort

        meta = json.loads((artifacts_dir / "tabular_onnx_meta.json").read_text(encoding="utf-8"))
        self.meta = meta
        self.feature_columns: list[str] = meta["feature_columns"]
        self.input_name: str = meta["input_name"]
        self.coef: float = meta["calibrator"]["coef"]
        self.intercept: float = meta["calibrator"]["intercept"]
        self.t1: float = meta["thresholds"]["t1"]
        self.t2: float = meta["thresholds"]["t2"]
        self.preprocess = joblib.load(artifacts_dir / meta["preprocess_file"])
        self.session = ort.InferenceSession(
            (artifacts_dir / meta["onnx_file"]).read_bytes(), providers=["CPUExecutionProvider"])

    def _matrix(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = self.preprocess.transform(frame)
        if hasattr(matrix, "toarray"):
            matrix = matrix.toarray()
        dense = np.asarray(matrix, dtype=np.float32)
        dense = np.where(dense == 0.0, np.nan, dense).astype(np.float32)  # sparse zeros are missing
        return np.ascontiguousarray(dense)

    def _feature_frame(self, raw: pd.DataFrame) -> pd.DataFrame:
        engineered = features(raw)
        for column in self.feature_columns:
            if column not in engineered.columns and column in raw.columns:
                engineered[column] = raw[column].values
        return engineered[self.feature_columns]

    def score(self, raw: pd.DataFrame) -> pd.DataFrame:
        X = self._feature_frame(raw)
        outputs = self.session.run(None, {self.input_name: self._matrix(X)})
        raw_probability = None
        for output in outputs:
            array = np.asarray(output)
            if array.ndim == 2 and array.shape[1] == 2:
                raw_probability = array[:, 1]
                break
        if raw_probability is None:
            raise RuntimeError("ONNX model did not return a 2-column probability output.")
        clipped = np.clip(raw_probability, 1e-6, 1 - 1e-6)
        logit = np.log(clipped / (1 - clipped))
        probability = 1.0 / (1.0 + np.exp(-(self.coef * logit + self.intercept)))
        action = np.where(probability >= self.t2, "SIU_review",
                          np.where(probability >= self.t1, "manual_review", "straight_through_candidate"))
        result = {"fraud_risk_score": probability, "suggested_queue": action}
        if "claim_id" in raw.columns:
            result = {"claim_id": raw["claim_id"].to_numpy(), **result}
        return pd.DataFrame(result)
