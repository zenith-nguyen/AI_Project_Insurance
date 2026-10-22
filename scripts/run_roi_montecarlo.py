"""Run the Business Case Monte Carlo and lock the review operating point (t1, t2).

Scores val_fs with B2 (XGBoost), then for each prevalence scenario draws the
net-value-vs-capacity curve, picks (t1, t2) that maximize expected net value
under the K1/K2 capacity caps, and runs Monte Carlo over the declared cost
distributions. Every figure is a scenario conditioned on PLACEHOLDER assumptions
in configs/business_assumptions_montecarlo.v1.yaml, not a measured outcome.

Run:
    python scripts/run_roi_montecarlo.py
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.data.common import config
from src.features.preprocessing import features
from src.models.train import _pipeline
from src.simulation.montecarlo_roi import (
    choose_operating_point, net_value_by_capacity, queue_rates, simulate_net_value, summarize,
)

OUT = ROOT / "reports/business_case"
MILLION = 1_000_000


def _b2_scores():
    fs = ROOT / "data/gold/feature_selection_v1"
    train, val = pd.read_parquet(fs / "train_fs.parquet"), pd.read_parquet(fs / "val_fs.parquet")
    x_train, x_val = features(train), features(val)
    y_train = train.fraud_label.astype(int).to_numpy()
    y_val = val.fraud_label.astype(int).to_numpy()
    probs = _pipeline("xgboost", x_train, config("params.yaml")["seed"]).fit(x_train, y_train).predict_proba(x_val)[:, 1]
    return probs[y_val == 1], probs[y_val == 0]


def main() -> int:
    cfg = config("configs/business_assumptions_montecarlo.v1.yaml")
    dists = cfg["distributions"]
    portfolio = int(cfg["portfolio_claims"])
    k1, k2 = cfg["constraints"]["K1_max_total_review_rate"], cfg["constraints"]["K2_max_siu_rate"]
    iterations = int(cfg["monte_carlo"]["iterations"])
    seed = int(cfg["monte_carlo"]["seed"])
    scenarios = [float(p) for p in cfg["prevalence_scenarios"]]
    pos, neg = _b2_scores()
    OUT.mkdir(parents=True, exist_ok=True)

    results, curves = {}, {}
    for prevalence in scenarios:
        rng = np.random.default_rng(seed)
        best = choose_operating_point(pos, neg, dists, prevalence, portfolio, k1, k2)
        rates = queue_rates(pos, neg, best["t1"], best["t2"], prevalence)
        draws = simulate_net_value(rates, dists, portfolio, rng, iterations)
        results[f"prevalence_{prevalence}"] = {
            "operating_point": {"t1": best["t1"], "t2": best["t2"]},
            "total_review_rate": rates["total_review_rate"], "siu_rate": rates["siu_rate"],
            "fraud_recall_review_queue": rates["fraud_recall_review"],
            "net_value_vnd": summarize(draws),
        }
        curves[prevalence] = net_value_by_capacity(pos, neg, dists, prevalence, portfolio, k1, k2,
                                                   np.random.default_rng(seed), iterations)

    # Chart 1: net value vs capacity K, one line per scenario, band on the middle one.
    fig, axis = plt.subplots(figsize=(8, 5))
    colors = {0.05: "#5b8ff9", 0.07: "#1f6f54", 0.10: "#c0504d"}
    for prevalence in scenarios:
        curve = curves[prevalence]
        xs = [c["capacity_k"] * 100 for c in curve]
        ys = [c["mean"] / MILLION for c in curve]
        color = colors.get(prevalence, None)
        axis.plot(xs, ys, marker="o", markersize=3, linewidth=2, color=color, label=f"prevalence {int(prevalence*100)}%")
        if prevalence == 0.07:
            axis.fill_between(xs, [c["p5"] / MILLION for c in curve], [c["p95"] / MILLION for c in curve],
                              color=color, alpha=0.12, label="CI 90% (prevalence 7%)")
        peak = max(curve, key=lambda c: c["mean"])
        axis.scatter([peak["capacity_k"] * 100], [peak["mean"] / MILLION], color=color, s=60, zorder=5, edgecolor="white")
    axis.axhline(0, color="#8a9799", linewidth=1)
    axis.set(xlabel="Tỷ lệ hồ sơ được review K (%)", ylabel="Giá trị ròng kỳ vọng (triệu VND / 10.000 hồ sơ)",
             title="Đường cong giá trị ròng theo K% (giả định placeholder)")
    axis.grid(alpha=0.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "roi_net_value_by_k.png", dpi=180); plt.close(fig)

    # Chart 2: net-value distribution at the operating point (middle scenario).
    base = 0.07 if 0.07 in scenarios else scenarios[len(scenarios) // 2]
    best = choose_operating_point(pos, neg, dists, base, portfolio, k1, k2)
    rates = queue_rates(pos, neg, best["t1"], best["t2"], base)
    draws = simulate_net_value(rates, dists, portfolio, np.random.default_rng(seed), iterations)
    fig, axis = plt.subplots(figsize=(8, 4.6))
    axis.hist(draws / MILLION, bins=50, color="#1f6f54", alpha=0.75)
    axis.axvline(float(np.mean(draws)) / MILLION, color="#1a1a1a", linewidth=1.5, label=f"Mean = {np.mean(draws)/MILLION:.1f} triệu")
    axis.axvline(0, color="#c0504d", linewidth=1, linestyle="--", label=f"P(NV>0) = {np.mean(draws>0):.2f}")
    axis.set(xlabel="Giá trị ròng (triệu VND / 10.000 hồ sơ)", ylabel="Số lần mô phỏng",
             title=f"Phân phối giá trị ròng tại operating point · prevalence {int(base*100)}%")
    axis.grid(alpha=0.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "roi_net_value_distribution.png", dpi=180); plt.close(fig)

    report = {
        "status": cfg["status"],
        "currency": cfg["currency"],
        "portfolio_claims": portfolio,
        "constraints": {"K1_max_total_review_rate": k1, "K2_max_siu_rate": k2},
        "monte_carlo": {"iterations": iterations, "seed": seed},
        "scoring_model": "B2 XGBoost on feature_selection_v1/val_fs",
        "scenarios": results,
        "caveat": "Scenario conditioned on placeholder cost distributions; not a measured business outcome. Confirm real costs before use.",
    }
    (OUT / "roi_montecarlo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: {"t1": round(v["operating_point"]["t1"], 4), "t2": round(v["operating_point"]["t2"], 4),
                          "review_rate": round(v["total_review_rate"], 4), "siu_rate": round(v["siu_rate"], 4),
                          "mean_net_value_million": round(v["net_value_vnd"]["mean"] / MILLION, 1),
                          "prob_positive": round(v["net_value_vnd"]["prob_positive"], 3)}
                      for k, v in results.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
