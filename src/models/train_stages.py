"""Train separate research scorecards for intake and complete-file checkpoints."""
from __future__ import annotations

import json
import platform

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict

from src.data.common import ROOT, config, utc_now, write_json
from src.evaluation.metrics import evaluate, stratified_bootstrap
from src.evaluation.operations import choose_thresholds, operational_metrics
from src.features.preprocessing import features
from src.models.train import _load_splits, _pipeline


def _platt_input(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def train_stage(name: str, columns: list[str], splits: dict[str, pd.DataFrame], params: dict) -> dict:
    x = {part: features(frame)[columns] for part, frame in splits.items()}
    y = {part: frame.fraud_label.astype(int).to_numpy() for part, frame in splits.items()}
    cv = RepeatedStratifiedKFold(n_splits=params["cv"]["n_splits"], n_repeats=params["cv"]["n_repeats"], random_state=params["seed"])
    candidates = {}
    for model_name in ("logreg", "xgboost"):
        fold_metrics = []
        for train_idx, holdout_idx in cv.split(x["train"], y["train"]):
            model = _pipeline(model_name, x["train"], params["seed"])
            model.fit(x["train"].iloc[train_idx], y["train"][train_idx])
            predictions = model.predict_proba(x["train"].iloc[holdout_idx])[:, 1]
            fold_metrics.append(evaluate(y["train"][holdout_idx], predictions, (0.1,)))
        candidates[model_name] = {
            "average_precision_mean": float(np.mean([metric["average_precision"] for metric in fold_metrics])),
            "recall_at_10pct_mean": float(np.mean([metric["recall_at_10pct"] for metric in fold_metrics])),
            "fold_count": len(fold_metrics),
        }
    selected = max(candidates, key=lambda model_name: candidates[model_name]["average_precision_mean"])
    model = _pipeline(selected, x["train"], params["seed"])
    oof = cross_val_predict(clone(model), x["train"], y["train"], cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=params["seed"]), method="predict_proba")[:, 1]
    calibrator = LogisticRegression(random_state=params["seed"]).fit(_platt_input(oof), y["train"])
    model.fit(x["train"], y["train"])
    val_scores = calibrator.predict_proba(_platt_input(model.predict_proba(x["val"])[:, 1]))[:, 1]
    test_scores = calibrator.predict_proba(_platt_input(model.predict_proba(x["test"])[:, 1]))[:, 1]
    thresholds = choose_thresholds(val_scores, params["operations"]["review_capacity"], params["operations"]["siu_capacity"])
    artifact = ROOT / "artifacts/models" / f"{name}_v1"
    artifact.mkdir(parents=True, exist_ok=True)
    joblib.dump({"stage": name, "model": model, "calibrator": calibrator, "thresholds": thresholds, "feature_columns": columns, "research_only": True}, artifact / "bundle.joblib")
    prediction_path = ROOT / "reports/metrics" / f"{name}_test_predictions.csv"
    pd.DataFrame({"claim_id": splits["test"].claim_id, "fraud_label": y["test"], "score": test_scores}).to_csv(prediction_path, index=False)
    return {
        "stage": name, "feature_columns": columns, "selected_model": selected, "cv_train": candidates,
        "calibration": "sigmoid fitted on out-of-fold train scores", "validation": evaluate(y["val"], val_scores, (0.1, 0.2), probability=True),
        "test": evaluate(y["test"], test_scores, (0.1, 0.2), probability=True),
        "test_ci_95": stratified_bootstrap(y["test"], test_scores, 0.1, params["evaluation"]["bootstrap_samples"], params["seed"]),
        "thresholds_from_validation": thresholds, "test_operations": operational_metrics(y["test"], test_scores, thresholds),
    }


def run() -> dict:
    params = config("params.yaml")
    stages = config("configs/stages.yaml")
    splits, gold = _load_splits()
    available = set(features(splits["train"]).columns)
    for name, stage in stages.items():
        missing = sorted(set(stage["features"]) - available)
        if missing:
            raise ValueError(f"{name} missing features: {missing}")
    results = {name: train_stage(name, stage["features"], splits, params) for name, stage in stages.items()}
    report = {
        "created_at_utc": utc_now(), "gold_version": gold["version"], "gold_test_sha256": gold["splits"]["test"]["sha256"],
        "stages": results, "status": "research only; feature availability and label provenance unverified",
        "warnings": ["Stage 1 incident fields may be incomplete at initial intake", "Stage 3 claim details require temporal availability confirmation", "Scores are calibrated to Kaggle source prevalence, not production prevalence", "Two-stage results use one frozen test; do not select the better stage by test performance"],
        "versions": {"python": platform.python_version(), "pandas": pd.__version__},
    }
    write_json(ROOT / "reports/metrics/stages_v1.json", report)
    return report


if __name__ == "__main__":
    output = run()
    print(json.dumps({name: {"selected_model": result["selected_model"], "test": result["test"]} for name, result in output["stages"].items()}, indent=2))
