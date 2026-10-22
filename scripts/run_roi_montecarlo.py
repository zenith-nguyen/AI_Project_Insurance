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
    bootstrap_operating_point, choose_operating_point, fixed_point_regret,
    net_value_by_capacity, queue_rates, simulate_net_value, summarize,
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

    base = 0.07 if 0.07 in scenarios else scenarios[len(scenarios) // 2]

    # Capacity sensitivity at the base prevalence (operational decision, not a cost change).
    sensitivity = []
    for profile in cfg.get("capacity_profiles", []):
        point = choose_operating_point(pos, neg, dists, base, portfolio, profile["K1"], profile["K2"])
        prof_rates = queue_rates(pos, neg, point["t1"], point["t2"], base)
        prof_draws = simulate_net_value(prof_rates, dists, portfolio, np.random.default_rng(seed), iterations)
        sensitivity.append({"name": profile["name"], "K1": profile["K1"], "K2": profile["K2"],
                            "t1": point["t1"], "t2": point["t2"],
                            "total_review_rate": prof_rates["total_review_rate"], "siu_rate": prof_rates["siu_rate"],
                            "fraud_recall_review": prof_rates["fraud_recall_review"],
                            "net_value_vnd": summarize(prof_draws)})

    if sensitivity:
        fig, axis = plt.subplots(figsize=(7.5, 4.4))
        names = [f"{s['name']}\nK1={int(s['K1']*100)}% K2={int(s['K2']*100)}%" for s in sensitivity]
        means = [s["net_value_vnd"]["mean"] / MILLION for s in sensitivity]
        lo = [s["net_value_vnd"]["mean"] / MILLION - s["net_value_vnd"]["p5"] / MILLION for s in sensitivity]
        hi = [s["net_value_vnd"]["p95"] / MILLION - s["net_value_vnd"]["mean"] / MILLION for s in sensitivity]
        axis.bar(names, means, color="#1f6f54", alpha=0.8, yerr=[lo, hi], capsize=5, ecolor="#8a9799")
        for i, s in enumerate(sensitivity):
            axis.text(i, means[i], f"{means[i]:.0f}", ha="center", va="bottom", fontsize=9)
        axis.set(ylabel="Giá trị ròng kỳ vọng (triệu VND / 10.000 hồ sơ)",
                 title=f"Độ nhạy theo capacity K1/K2 · prevalence {int(base*100)}% (giả định placeholder)")
        axis.grid(alpha=0.2, axis="y")
        fig.tight_layout(); fig.savefig(OUT / "roi_capacity_sensitivity.png", dpi=180); plt.close(fig)

    # Chart 2: net-value distribution at the operating point (middle scenario).
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

    # Sampling uncertainty from the 140-row validation set (bootstrap), combined with cost MC.
    boot = bootstrap_operating_point(pos, neg, dists, base, portfolio, k1, k2, np.random.default_rng(seed))
    fig, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.hist(boot["_draws"] / MILLION, bins=50, color="#5b8ff9", alpha=0.75)
    axis.axvline(boot["net_value"]["mean"] / MILLION, color="#1a1a1a", linewidth=1.5,
                 label=f"Mean = {boot['net_value']['mean']/MILLION:.0f} triệu")
    axis.axvline(0, color="#c0504d", linewidth=1, linestyle="--", label=f"P(NV>0) = {boot['net_value']['prob_positive']:.2f}")
    axis.set(xlabel="Giá trị ròng (triệu VND / 10.000 hồ sơ)", ylabel="Số lần mô phỏng",
             title=f"GTR gộp bất định chi phí + lấy mẫu val_fs · prevalence {int(base*100)}%")
    axis.grid(alpha=0.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "roi_sampling_bootstrap.png", dpi=180); plt.close(fig)

    # Regret of deploying one fixed operating point (chosen at base prevalence) across scenarios.
    regret = fixed_point_regret(pos, neg, dists, best["t1"], best["t2"], scenarios, portfolio, k1, k2)
    fig, axis = plt.subplots(figsize=(7.5, 4.2))
    x = np.arange(len(regret)); width = 0.38
    axis.bar(x - width / 2, [r["oracle_net_value"] / MILLION for r in regret], width, label="Tối ưu theo prevalence", color="#1f6f54", alpha=0.85)
    axis.bar(x + width / 2, [r["fixed_net_value"] / MILLION for r in regret], width, label=f"Điểm cố định (t1={best['t1']:.2f}, t2={best['t2']:.2f})", color="#9bbcab", alpha=0.95)
    axis.set_xticks(x); axis.set_xticklabels([f"{int(r['prevalence']*100)}%" for r in regret])
    axis.set(xlabel="Prevalence", ylabel="Giá trị ròng kỳ vọng (triệu VND)", title="Regret của operating point cố định")
    axis.grid(alpha=0.2, axis="y"); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "roi_fixed_point_regret.png", dpi=180); plt.close(fig)

    report = {
        "status": cfg["status"],
        "currency": cfg["currency"],
        "portfolio_claims": portfolio,
        "constraints": {"K1_max_total_review_rate": k1, "K2_max_siu_rate": k2},
        "monte_carlo": {"iterations": iterations, "seed": seed},
        "scoring_model": "B2 XGBoost on feature_selection_v1/val_fs",
        "scenarios": results,
        "base_prevalence": base,
        "capacity_sensitivity": sensitivity,
        "sampling_bootstrap": {k: v for k, v in boot.items() if not k.startswith("_")},
        "fixed_point_regret": regret,
        "caveat": "Scenario conditioned on placeholder cost distributions; not a measured business outcome. Confirm real costs before use.",
    }
    (OUT / "roi_montecarlo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: {"t1": round(v["operating_point"]["t1"], 4), "t2": round(v["operating_point"]["t2"], 4),
                          "review_rate": round(v["total_review_rate"], 4), "siu_rate": round(v["siu_rate"], 4),
                          "mean_net_value_million": round(v["net_value_vnd"]["mean"] / MILLION, 1),
                          "prob_positive": round(v["net_value_vnd"]["prob_positive"], 3)}
                      for k, v in results.items()}, ensure_ascii=False, indent=2))
    print("capacity_sensitivity (prevalence %d%%):" % int(base * 100))
    print(json.dumps([{"profile": s["name"], "K1": s["K1"], "K2": s["K2"], "t1": round(s["t1"], 4), "t2": round(s["t2"], 4),
                       "review_rate": round(s["total_review_rate"], 4), "siu_rate": round(s["siu_rate"], 4),
                       "mean_net_value_million": round(s["net_value_vnd"]["mean"] / MILLION, 1)}
                      for s in sensitivity], ensure_ascii=False, indent=2))
    print("sampling_bootstrap (prevalence %d%%, n_boot=%d):" % (int(base * 100), boot["n_boot"]))
    print(json.dumps({"t1_p5_med_p95": [round(boot["t1"]["p5"], 3), round(boot["t1"]["median"], 3), round(boot["t1"]["p95"], 3)],
                      "review_rate_p5_med_p95": [round(boot["review_rate"]["p5"], 3), round(boot["review_rate"]["median"], 3), round(boot["review_rate"]["p95"], 3)],
                      "net_value_million": {"p5": round(boot["net_value"]["p5"] / MILLION, 0), "mean": round(boot["net_value"]["mean"] / MILLION, 0), "p95": round(boot["net_value"]["p95"] / MILLION, 0), "prob_positive": round(boot["net_value"]["prob_positive"], 3)}}, ensure_ascii=False, indent=2))
    print("fixed_point_regret:")
    print(json.dumps([{"prevalence": r["prevalence"], "fixed_million": round(r["fixed_net_value"] / MILLION, 1),
                       "oracle_million": round(r["oracle_net_value"] / MILLION, 1), "regret_pct": round(r["regret_pct"] * 100, 1)}
                      for r in regret], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
