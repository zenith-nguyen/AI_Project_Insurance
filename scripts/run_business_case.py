"""Charts, sensitivity and report for Thanh Vy's canonical business case model.

The economic model is scripts/monte_carlo_business_case.py (Thanh Vy, authoritative).
This runner only consumes its simulate()/summary() to draw figures, sweep the claim
volume N, find the break-even N, and write a report. It adds nothing to the model.

Run:
    python scripts/run_business_case.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import monte_carlo_business_case as mcbc

OUT = ROOT / "reports/business_case"
BILLION = 1_000_000_000
ITERS = 10_000        # headline run
ITERS_SWEEP = 4_000   # cheaper runs for the N sensitivity (per-iteration DPP loop is slow)
BASE_N = mcbc.DECISION["N"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    res = mcbc.simulate(ITERS, dec={"N": BASE_N})
    s = mcbc.summary(res)
    s["IRR_median_flows"] = mcbc.irr_of_median(res)

    npv, dnv = res["NPV"] / BILLION, res["dNV"] / BILLION
    nv_ai, nv_rule = res["A"]["NV"] / BILLION, res["B"]["NV"] / BILLION

    # Chart 1: incremental NPV (3 years).
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.hist(npv, bins=70, color="#1f6f54", alpha=0.78)
    ax.axvline(float(np.median(npv)), color="#1a1a1a", lw=1.5, label=f"Trung vị = {np.median(npv):.2f} tỷ")
    ax.axvline(0, color="#c0504d", lw=1, ls="--", label=f"P(NPV>0) = {s['P(NPV_inc>0)']:.2f}")
    ax.set(xlabel="NPV tăng thêm 3 năm (tỷ VND)", ylabel="Số lần", title=f"Phân phối NPV · N={BASE_N:,} · 10.000 lần, seed 2026")
    ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(OUT / "bc_npv_distribution.png", dpi=180); plt.close(fig)

    # Chart 2: annual delta NV.
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.hist(dnv, bins=70, color="#5b8ff9", alpha=0.78)
    ax.axvline(float(np.median(dnv)), color="#1a1a1a", lw=1.5, label=f"Trung vị = {np.median(dnv):.2f} tỷ/năm")
    ax.axvline(0, color="#c0504d", lw=1, ls="--", label=f"P(ΔNV>0) = {s['P(dNV>0)']:.2f}")
    ax.set(xlabel="ΔNV hằng năm, AI so với luật (tỷ VND)", ylabel="Số lần", title="Giá trị ròng tăng thêm của AI so với luật")
    ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(OUT / "bc_delta_nv.png", dpi=180); plt.close(fig)

    # Chart 3: NV_AI vs NV_rule.
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.hist(nv_rule, bins=70, color="#9bbcab", alpha=0.7, label=f"NV luật (trung vị {np.median(nv_rule):.2f} tỷ)")
    ax.hist(nv_ai, bins=70, color="#1f6f54", alpha=0.6, label=f"NV AI (trung vị {np.median(nv_ai):.2f} tỷ)")
    ax.axvline(0, color="#c0504d", lw=1, ls="--")
    ax.set(xlabel="Net Value hằng năm (tỷ VND)", ylabel="Số lần", title="Net Value: AI so với luật cứng")
    ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(OUT / "bc_nv_ai_vs_rule.png", dpi=180); plt.close(fig)

    # Chart 4: discounted payback period (DPP), finite cases only.
    dpp = res["DPP"]
    finite = dpp[np.isfinite(dpp)]
    p_le3 = float((dpp <= 3).mean())
    fig, ax = plt.subplots(figsize=(8, 4.4))
    if finite.size:
        ax.hist(np.clip(finite, 0, 3), bins=40, color="#d08a1f", alpha=0.8)
        ax.axvline(float(np.median(finite)), color="#1a1a1a", lw=1.5,
                   label=f"Trung vị (khi hoàn vốn) = {np.median(finite):.2f} năm")
    ax.axvline(3, color="#c0504d", lw=1, ls="--", label=f"P(DPP≤3 năm) = {p_le3:.2f}")
    ax.set(xlabel="Thời gian hoàn vốn chiết khấu (năm)", ylabel="Số lần",
           title="Phân phối DPP (chỉ các kịch bản hoàn vốn trong 3 năm)", xlim=(0, 3.2))
    ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(OUT / "bc_dpp.png", dpi=180); plt.close(fig)

    # Sensitivity + break-even on N.
    N_grid = [10_000, 20_000, 30_000, 40_000, 50_000, 75_000, 100_000]
    med_npv, prob_pos = [], []
    for value in N_grid:
        r = mcbc.simulate(ITERS_SWEEP, dec={"N": value})
        med_npv.append(float(np.median(r["NPV"])) / BILLION)
        prob_pos.append(float((r["NPV"] > 0).mean()))
    # Locate where median NPV crosses 0 by interpolating the grid above.
    breakeven_N = None
    for a, b, va, vb in zip(N_grid[:-1], N_grid[1:], med_npv[:-1], med_npv[1:]):
        if va < 0 <= vb:
            breakeven_N = int(a + (b - a) * (0 - va) / (vb - va)); break

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].plot([n / 1000 for n in N_grid], med_npv, marker="o", color="#1f6f54", lw=2)
    axes[0].axhline(0, color="#8a9799", lw=1)
    if breakeven_N:
        axes[0].axvline(breakeven_N / 1000, color="#c0504d", ls="--", lw=1, label=f"Hoà vốn N≈{breakeven_N:,}")
        axes[0].legend(fontsize=8)
    axes[0].set(xlabel="N (nghìn hồ sơ/năm)", ylabel="NPV trung vị (tỷ VND)", title="NPV trung vị theo N"); axes[0].grid(alpha=.2)
    axes[1].plot([n / 1000 for n in N_grid], prob_pos, marker="o", color="#5b8ff9", lw=2)
    axes[1].axhline(0.5, color="#8a9799", ls="--", lw=1)
    axes[1].set(xlabel="N (nghìn hồ sơ/năm)", ylabel="P(NPV>0)", title="Xác suất NPV>0 theo N", ylim=(0, 1)); axes[1].grid(alpha=.2)
    fig.tight_layout(); fig.savefig(OUT / "bc_sensitivity.png", dpi=180); plt.close(fig)

    report = {
        "status": "real_assumptions_from_thanh_vy",
        "engine": "scripts/monte_carlo_business_case.py (canonical, Thanh Vy)",
        "base_decision": mcbc.DECISION,
        "summary": s,
        "sensitivity_N": {"N": N_grid, "median_npv_billion": med_npv, "prob_npv_positive": prob_pos},
        "breakeven_N_median_npv": breakeven_N,
    }
    (OUT / "business_case_v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "N": BASE_N, "Recall_AI_med": round(s["Recall_AI"][1], 4), "Recall_rule_med": round(s["Recall_rule"][1], 4),
        "NPV_inc_billion_p5_med_p95": [round(x / BILLION, 2) for x in s["NPV_inc"]],
        "ROI_inc_med": round(s["ROI_inc"][1], 3), "DPP_med": round(s["DPP_median_if_finite"], 2),
        "P(NPV>0)": s["P(NPV_inc>0)"], "P(dNV>0)": s["P(dNV>0)"], "P(Prec>Prec*)": s["P(Precision>Prec*)"],
        "breakeven_N": breakeven_N,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
