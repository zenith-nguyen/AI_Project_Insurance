"""Select on train CV, calibrate from train OOF, set queues on validation, evaluate once on test."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.metrics import average_precision_score
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from src.baselines.rules import RuleBaseline
from src.data.common import ROOT, config, sha256, utc_now, write_json
from src.evaluation.metrics import evaluate, stratified_bootstrap
from src.evaluation.operations import choose_thresholds, operational_metrics
from src.evaluation.prevalence import scenario_at_k
from src.features.leakage_audit import write_report
from src.features.preprocessing import features, preprocessor


def _model(name: str, seed: int):
    spec = config("configs/models.yaml")[name]
    if name == "logreg":
        return LogisticRegression(**spec, random_state=seed)
    if name == "random_forest":
        return RandomForestClassifier(**spec, random_state=seed, n_jobs=1)
    if name == "xgboost":
        return XGBClassifier(**spec, random_state=seed, n_jobs=1, eval_metric="logloss", tree_method="hist")
    return LGBMClassifier(**spec, random_state=seed, n_jobs=1, verbosity=-1)


def _pipeline(name: str, x: pd.DataFrame, seed: int) -> Pipeline:
    return Pipeline([("preprocess", preprocessor(x, scale_numeric=name == "logreg")), ("model", _model(name, seed))])


def _load_splits() -> tuple[dict[str, pd.DataFrame], dict]:
    folder = ROOT / "data/gold" / config("params.yaml")["gold"]["version"]
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    splits = {}
    for name in ("train", "val", "test"):
        path = folder / f"{name}.parquet"
        if sha256(path) != manifest["splits"][name]["sha256"]:
            raise ValueError(f"Gold {name} hash mismatch")
        splits[name] = pd.read_parquet(path)
    return splits, manifest


def run() -> dict:
    params = config("params.yaml")
    splits, gold_manifest = _load_splits()
    write_report(splits["train"])
    x = {name: features(frame) for name, frame in splits.items()}
    y = {name: frame.fraud_label.astype(int).to_numpy() for name, frame in splits.items()}
    if any(list(x[name].columns) != list(x["train"].columns) for name in ("val", "test")):
        raise ValueError("Feature schema mismatch between Gold splits")
    cv = RepeatedStratifiedKFold(n_splits=params["cv"]["n_splits"], n_repeats=params["cv"]["n_repeats"], random_state=params["seed"])
    cv_results = {}
    for name in ("logreg", "random_forest", "xgboost", "lightgbm"):
        fold_scores = []
        for train_idx, holdout_idx in cv.split(x["train"], y["train"]):
            pipe = _pipeline(name, x["train"], params["seed"])
            pipe.fit(x["train"].iloc[train_idx], y["train"][train_idx])
            predictions = pipe.predict_proba(x["train"].iloc[holdout_idx])[:, 1]
            fold_scores.append(evaluate(y["train"][holdout_idx], predictions, params["evaluation"]["k_values"]))
        cv_results[name] = {metric: float(np.mean([fold[metric] for fold in fold_scores])) for metric in ("average_precision", "roc_auc", "recall_at_10pct", "precision_at_10pct")}
        cv_results[name]["fold_count"] = len(fold_scores)
    winner = max(cv_results, key=lambda name: (cv_results[name]["average_precision"], cv_results[name]["recall_at_10pct"]))
    model = _pipeline(winner, x["train"], params["seed"])
    # Out-of-fold train predictions fit a monotonic Platt map without using validation/test labels.
    oof = cross_val_predict(clone(model), x["train"], y["train"], cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=params["seed"]), method="predict_proba")[:, 1]
    calibrator = LogisticRegression(random_state=params["seed"])
    calibrator.fit(np.log(np.clip(oof, 1e-6, 1 - 1e-6) / np.clip(1 - oof, 1e-6, 1)).reshape(-1, 1), y["train"])
    isotonic = IsotonicRegression(out_of_bounds="clip").fit(oof, y["train"])
    model.fit(x["train"], y["train"])

    def calibrated(split: str) -> np.ndarray:
        raw = np.clip(model.predict_proba(x[split])[:, 1], 1e-6, 1 - 1e-6)
        return calibrator.predict_proba(np.log(raw / (1 - raw)).reshape(-1, 1))[:, 1]

    val_score = calibrated("val")
    isotonic_val = isotonic.predict(model.predict_proba(x["val"])[:, 1])
    test_score = calibrated("test")
    thresholds = choose_thresholds(val_score, params["operations"]["review_capacity"], params["operations"]["siu_capacity"])
    rule = RuleBaseline().fit(splits["train"])
    rule_test = rule.score(splits["test"])
    test_metrics = evaluate(y["test"], test_score, params["evaluation"]["k_values"], probability=True)
    rule_metrics = evaluate(y["test"], rule_test, params["evaluation"]["k_values"])
    result = {
        "created_at_utc": utc_now(), "dataset": "Kaggle insurance-fraud-detection tabular only", "gold_version": gold_manifest["version"], "gold_test_sha256": gold_manifest["splits"]["test"]["sha256"],
        "model_selection": "train repeated stratified CV mean average precision", "selected_model": winner, "cv": cv_results,
        "calibration": "sigmoid on train out-of-fold logits; isotonic exploratory only", "validation": evaluate(y["val"], val_score, params["evaluation"]["k_values"], probability=True),
        "validation_isotonic_brier_exploratory": float(brier_score_loss(y["val"], isotonic_val)),
        "test": test_metrics, "test_ci_95": stratified_bootstrap(y["test"], test_score, 0.1, params["evaluation"]["bootstrap_samples"], params["seed"]),
        "rule_baseline_test": rule_metrics, "thresholds_from_validation": thresholds,
        "test_operations": operational_metrics(y["test"], test_score, thresholds),
        "prevalence_scenarios": [scenario_at_k(y["test"], test_score, prevalence, k) for prevalence in params["evaluation"]["production_prevalence"] for k in params["evaluation"]["k_values"]],
        "limitations": ["Test has only about 49 fraud cases", "Prevalence scenarios assume stable class-conditional score distributions", "Source label provenance and feature availability need domain review", "Image/document modules are not claim-linked"],
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__, "pandas": pd.__version__},
    }
    output = ROOT / "reports/metrics"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "tabular_v1.json", result)
    predictions = splits["test"][["claim_id", "fraud_label"]].copy()
    predictions["calibrated_score"] = test_score
    predictions["rule_score"] = rule_test
    predictions.to_csv(output / "test_predictions.csv", index=False)
    artifacts = ROOT / "artifacts/models/tabular_v1"
    artifacts.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "calibrator": calibrator, "rules": rule, "thresholds": thresholds, "feature_columns": list(x["train"].columns)}, artifacts / "bundle.joblib")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    report = run()
    print(json.dumps({"selected_model": report["selected_model"], "test": report["test"], "rule_baseline_test": report["rule_baseline_test"]}, indent=2))
