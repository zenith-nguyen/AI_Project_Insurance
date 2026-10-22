"""Measure and improve B2 (XGBoost) probability calibration on val_fs.

Ranking metrics (AP, Recall@K) say nothing about whether a score reads as a
probability. This script measures calibration of the raw XGBoost output and of
two calibrators fitted only on out-of-fold train predictions (never on val),
then draws a reliability curve. Calibration is monotone, so AP and the queue
order are unchanged; only the probability reading improves.

val_fs has 35 positives, so binned calibration numbers are noisy: read them as
indicative, confirm on a larger claim-linked set before any operational use.

Run:
    python scripts/evaluate_b2_calibration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.data.common import config
from src.evaluation.metrics import evaluate
from src.features.preprocessing import features
from src.models.train import _pipeline

OUT_DIR = ROOT / "reports/phase5"
SEED = 42
EPS = 1e-6


def _logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p)).reshape(-1, 1)


def _reliability(y, p, bins=5):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (p > lo) & (p <= hi)
        if sel.any():
            rows.append({"mean_pred": float(p[sel].mean()), "obs_freq": float(y[sel].mean()), "count": int(sel.sum())})
    return rows


def main() -> int:
    fs = ROOT / "data/gold/feature_selection_v1"
    train = pd.read_parquet(fs / "train_fs.parquet")
    val = pd.read_parquet(fs / "val_fs.parquet")
    x_train, x_val = features(train), features(val)
    y_train = train.fraud_label.astype(int).to_numpy()
    y_val = val.fraud_label.astype(int).to_numpy()

    pipe = _pipeline("xgboost", x_train, SEED)
    # Out-of-fold train probabilities to fit calibrators without leakage.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof = cross_val_predict(clone(pipe), x_train, y_train, cv=cv, method="predict_proba")[:, 1]
    pipe.fit(x_train, y_train)
    raw_val = pipe.predict_proba(x_val)[:, 1]

    platt = LogisticRegression(max_iter=1000).fit(_logit(oof), y_train)
    isotonic = IsotonicRegression(out_of_bounds="clip").fit(oof, y_train)
    variants = {
        "raw": raw_val,
        "platt": platt.predict_proba(_logit(raw_val))[:, 1],
        "isotonic": isotonic.predict(raw_val),
    }

    summary = {}
    for name, probs in variants.items():
        metric = evaluate(y_val, probs, k_values=(0.10,), probability=True)
        summary[name] = {
            "average_precision": metric["average_precision"],
            "brier": metric["brier"],
            "ece_10_bins": metric["ece_10_bins"],
            "mean_predicted": float(probs.mean()),
            "observed_prevalence": float(y_val.mean()),
            "reliability_5_quantile_bins": _reliability(y_val, probs),
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(6.2, 6))
    axis.plot([0, 1], [0, 1], "--", color="#8a9799", linewidth=1, label="Hiệu chuẩn hoàn hảo")
    for name, probs in variants.items():
        rel = _reliability(y_val, probs)
        axis.plot([r["mean_pred"] for r in rel], [r["obs_freq"] for r in rel], marker="o", linewidth=2,
                  label=f"{name} · Brier={summary[name]['brier']:.3f} · ECE={summary[name]['ece_10_bins']:.3f}")
    axis.axhline(float(y_val.mean()), color="#c0c0c0", linewidth=0.8)
    axis.set(xlabel="Xác suất dự đoán trung bình", ylabel="Tần suất Y quan sát",
             title="B2 XGBoost · Reliability curve (val_fs)", xlim=(0, 1), ylim=(0, 1))
    axis.grid(alpha=0.2); axis.legend(fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT_DIR / "b2_reliability.png", dpi=180); plt.close(fig)

    report = {
        "split": "feature_selection_v1/val_fs",
        "n": int(len(y_val)),
        "positives": int(y_val.sum()),
        "note": "val_fs has 35 positives; binned calibration is noisy. Calibration is monotone so AP and queue order are unchanged.",
        "variants": summary,
    }
    (OUT_DIR / "b2_calibration.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"brier": summary[name]["brier"], "ece_10_bins": summary[name]["ece_10_bins"],
                             "average_precision": summary[name]["average_precision"]} for name in variants},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
