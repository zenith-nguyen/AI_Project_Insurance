"""Optional CPU backend for the tabular estimator, using the original preprocessing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def float32_matrix(transformed) -> np.ndarray:
    """Sparse implicit entries are missing for XGBoost, not numeric zeros."""
    if sparse.issparse(transformed):
        coo = transformed.tocoo()
        result = np.full(coo.shape, np.nan, dtype=np.float32)
        result[coo.row, coo.col] = coo.data.astype(np.float32)
        return result
    return np.asarray(transformed, dtype=np.float32)


def positive_probability(outputs: list, row_count: int) -> np.ndarray:
    for value in outputs:
        if isinstance(value, np.ndarray) and value.shape == (row_count, 2):
            return value[:, 1].astype(np.float64)
        if isinstance(value, list) and len(value) == row_count and all(isinstance(row, dict) for row in value):
            return np.asarray([row.get(1, row.get("1")) for row in value], dtype=np.float64)
    raise ValueError("ONNX classifier has no recognizable binary probability output")


class OnnxTabularEstimator:
    def __init__(self, directory: str | Path, bundle_path: str | Path) -> None:
        import onnxruntime as ort

        directory, bundle_path = Path(directory), Path(bundle_path)
        manifest = json.loads((directory / "validation.json").read_text(encoding="utf-8"))
        model_file = directory / "tabular_xgboost.onnx"
        if manifest["status"] != "parity_passed" or manifest["scope"] != "xgboost_estimator_only":
            raise ValueError("ONNX artifact did not pass the export gate")
        if sha256(bundle_path) != manifest["bundle_sha256"] or sha256(model_file) != manifest["onnx_sha256"]:
            raise ValueError("ONNX and fitted bundle hashes do not match the validation report")
        self.feature_count = int(manifest["transformed_feature_count"])
        self.session = ort.InferenceSession(str(model_file), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def predict_raw(self, fitted_preprocessor, raw_frame) -> np.ndarray:
        matrix = float32_matrix(fitted_preprocessor.transform(raw_frame))
        if matrix.ndim != 2 or matrix.shape[1] != self.feature_count:
            raise ValueError("ONNX input dimensions differ from exported preprocessing")
        outputs = self.session.run(None, {self.input_name: matrix})
        return positive_probability(outputs, len(raw_frame))
