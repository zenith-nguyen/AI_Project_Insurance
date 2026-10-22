"""Run the full Monte Carlo business case (NV, NPV, ROI, DPP) on Thanh Vy's assumptions.

Reads configs/business_case_v2_thanh_vy.yaml, runs 10,000 iterations, and writes a
report plus charts to reports/business_case/. Structural scalars (N, discount rate,
SIU split) are researched estimates until the source doc confirms them, so N and the
discount rate are also swept for sensitivity.

Run:
    python scripts/run_business_case.py
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.data.common import config
from src.simulation.business_case import simulate

OUT = ROOT / "reports/business_case"
BILLION = 1_000_000_000


def main() -> int:
    cfg = config("configs/business_case_v2_thanh_vy.yaml")
    result = simulate(cfg)
    draws = result.pop("_draws")
    OUT.mkdir(parents=True, exist_ok=True)

    # Chart 1: NPV distribution.
    fig, axis = plt.subplots(figsize=(8, 4.4))
    axis.hist(draws["npv"] / BILLION, bins=60, color="#1f6f54", alpha=0.78)
    axis.axvline(result["npv"]["median"] / BILLION, color="#1a1a1a", linewidth=1.5, label=f"Trung vị = {result['npv']['median']/BILLION:.1f} tỷ")
    axis.axvline(0, color="#c0504d", linewidth=1, linestyle="--", label=f"P(NPV>0) = {result['probabilities']['npv_positive']:.2f}")
    axis.set(xlabel="NPV 3 năm (tỷ VND)", ylabel="Số lần mô phỏng", title="Phân phối NPV (10.000 lần, seed 2026)")
    axis.grid(alpha=0.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "bc_npv_distribution.png", dpi=180); plt.close(fig)

    # Chart 2: annual delta NV.
    fig, axis = plt.subplots(figsize=(8, 4.4))
    axis.hist(draws["dnv"] / BILLION, bins=60, color="#5b8ff9", alpha=0.78)
    axis.axvline(result["dnv_annual"]["median"] / BILLION, color="#1a1a1a", linewidth=1.5, label=f"Trung vị = {result['dnv_annual']['median']/BILLION:.2f} tỷ/năm")
    axis.axvline(0, color="#c0504d", linewidth=1, linestyle="--", label=f"P(ΔNV>0) = {result['probabilities']['delta_nv_positive']:.2f}")
    axis.set(xlabel="ΔNV hằng năm, AI so với luật (tỷ VND)", ylabel="Số lần mô phỏng", title="Giá trị ròng tăng thêm của AI so với luật")
    axis.grid(alpha=0.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "bc_delta_nv.png", dpi=180); plt.close(fig)

    # Sensitivity on the two researched structural scalars.
    N_grid = [20000, 40000, 60000, 80000, 100000]
    r_grid = [0.08, 0.10, 0.12, 0.14, 0.16]
    npv_by_N, npv_by_r = [], []
    for value in N_grid:
        c = copy.deepcopy(cfg); c["structural"]["annual_claim_volume_N"] = value
        npv_by_N.append(simulate(c)["npv"]["median"] / BILLION)
    for value in r_grid:
        c = copy.deepcopy(cfg); c["structural"]["discount_rate"] = value
        npv_by_r.append(simulate(c)["npv"]["median"] / BILLION)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].plot([n / 1000 for n in N_grid], npv_by_N, marker="o", color="#1f6f54", linewidth=2)
    axes[0].axhline(0, color="#8a9799", linewidth=1); axes[0].set(xlabel="N (nghìn hồ sơ/năm)", ylabel="NPV trung vị (tỷ VND)", title="Độ nhạy theo N")
    axes[0].grid(alpha=0.2)
    axes[1].plot([x * 100 for x in r_grid], npv_by_r, marker="o", color="#c0504d", linewidth=2)
    axes[1].axhline(0, color="#8a9799", linewidth=1); axes[1].set(xlabel="Lãi suất chiết khấu (%)", ylabel="NPV trung vị (tỷ VND)", title="Độ nhạy theo lãi suất")
    axes[1].grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(OUT / "bc_sensitivity.png", dpi=180); plt.close(fig)

    result["sensitivity"] = {"npv_median_by_N_billion": dict(zip(map(str, N_grid), npv_by_N)),
                             "npv_median_by_discount_billion": dict(zip(map(str, r_grid), npv_by_r))}
    result["status"] = cfg["status"]
    result["note_formula"] = "NV/NPV/ROI/DPP reconstructed from the parameter table with standard capital budgeting; structural scalars are researched estimates pending the source doc."
    (OUT / "business_case_v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "recall_real_median": {"ai": round(result["recall_real"]["ai"]["median"], 4), "rule": round(result["recall_real"]["rule"]["median"], 4)},
        "dnv_annual_billion": {"p5": round(result["dnv_annual"]["p5"]/BILLION, 2), "median": round(result["dnv_annual"]["median"]/BILLION, 2), "p95": round(result["dnv_annual"]["p95"]/BILLION, 2)},
        "npv_billion": {"p5": round(result["npv"]["p5"]/BILLION, 2), "median": round(result["npv"]["median"]/BILLION, 2), "p95": round(result["npv"]["p95"]/BILLION, 2)},
        "roi_median": round(result["roi"]["median"], 2),
        "dpp_years_median": round(result["dpp_years"]["median"], 2),
        "probabilities": {k: round(v, 3) for k, v in result["probabilities"].items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
