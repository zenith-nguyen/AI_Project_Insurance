"""Monte Carlo business case: NV_AI, NV_rule, dNV, NPV, ROI, DPP.

Implements Thanh Vy's assumption set (configs/business_case_v2_thanh_vy.yaml):
Beta/log-normal/uniform parameter distributions, a Gaussian copula between the two
test recalls (measured on the same 49 claims), and the equal-variance binormal
shift that moves Recall@10% from the frozen-test prevalence to the real channel
prevalence. The net-value / NPV / ROI / DPP formula is reconstructed from the
parameter table with standard capital budgeting; the few structural scalars
(N, discount rate, SIU split) are researched estimates until the source doc
confirms them. Money is VND.
"""
from __future__ import annotations

import numpy as np
from scipy.special import erfc
from scipy.stats import beta as beta_dist
from scipy.stats import norm


# ---- parameter sampling ------------------------------------------------------

def _sample(spec: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    dist = spec["dist"]
    if dist == "beta":
        return rng.beta(float(spec["alpha"]), float(spec["beta"]), n)
    if dist == "lognormal":
        return float(spec["median"]) * np.exp(float(spec["sigma"]) * rng.standard_normal(n))
    if dist == "uniform":
        return rng.uniform(float(spec["low"]), float(spec["high"]), n)
    raise ValueError(f"Unsupported distribution: {dist}")


def _correlated_recalls(dists: dict, rho: float, rng: np.random.Generator, n: int):
    """Two Beta recalls linked by a Gaussian copula with correlation rho."""
    z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], size=n)
    u = norm.cdf(z)
    ai = beta_dist.ppf(u[:, 0], dists["recall_ai_test"]["alpha"], dists["recall_ai_test"]["beta"])
    rule = beta_dist.ppf(u[:, 1], dists["recall_rule_test"]["alpha"], dists["recall_rule_test"]["beta"])
    return ai, rule


# ---- binormal recall shift (vectorized) --------------------------------------

def _sf(x):
    return 0.5 * erfc(x / np.sqrt(2))


def _tau_vec(d, p, k):
    """Vectorized threshold so that p*sf(tau-d)+(1-p)*sf(tau)=k, per element."""
    lo = np.full_like(d, -12.0)
    hi = np.full_like(d, 12.0)
    for _ in range(80):
        mid = (lo + hi) / 2
        g = p * _sf(mid - d) + (1 - p) * _sf(mid) - k
        lo = np.where(g > 0, mid, lo)
        hi = np.where(g > 0, hi, mid)
    return (lo + hi) / 2


def shift_recalls(recall_test, prevalence_test: float, prevalence_target, k: float = 0.10):
    """Move Recall@k from the (fixed) test prevalence to per-draw target prevalence
    through the equal-variance binormal model. d is fitted to the test recall."""
    recall_test = np.asarray(recall_test, float)
    target = np.clip(recall_test, 1e-6, min(1.0, k / prevalence_test) - 1e-9)
    # Fit d at the fixed test prevalence via a precomputed recall(d) curve.
    d_grid = np.linspace(0.0, 8.0, 4000)
    recall_curve = _sf(_tau_vec(d_grid, prevalence_test, k) - d_grid)
    order = np.argsort(recall_curve)
    d = np.interp(target, recall_curve[order], d_grid[order])
    prevalence_target = np.asarray(prevalence_target, float)
    recall_real = _sf(_tau_vec(d, prevalence_target, k) - d)
    return np.minimum(recall_real, np.minimum(1.0, k / prevalence_target))


# ---- economic model ----------------------------------------------------------

def simulate(cfg: dict) -> dict:
    dists = cfg["distributions"]
    s = cfg["structural"]
    N = float(s["annual_claim_volume_N"])
    K = float(cfg["queue_capacity_K"])
    r = float(s["discount_rate"])
    horizon = int(s["horizon_years"])
    siu_frac = float(s["siu_rate_within_queue"])
    p_test = float(cfg["frozen_test_prevalence"])
    iterations = int(cfg["monte_carlo"]["iterations"])
    rng = np.random.default_rng(int(cfg["monte_carlo"]["seed"]))

    recall_ai_test, recall_rule_test = _correlated_recalls(dists, float(cfg["recall_correlation_rho"]), rng, iterations)
    p = _sample(dists["p_group_b"], rng, iterations)
    recall_ai = shift_recalls(recall_ai_test, p_test, p, K)
    recall_rule = shift_recalls(recall_rule_test, p_test, p, K)

    loss = _sample(dists["loss_per_case"], rng, iterations)
    eta = _sample(dists["eta_prevented"], rng, iterations)
    c_bs = _sample(dists["c_basic_review"], rng, iterations)
    c_siu = _sample(dists["c_siu"], rng, iterations)
    c_cskh = _sample(dists["c_cskh"], rng, iterations)
    dq = _sample(dists["churn_increase"], rng, iterations)
    v_kh = _sample(dists["customer_value"], rng, iterations)
    gpu = _sample(dists["infra_gpu_year"], rng, iterations)
    staff = _sample(dists["staff_ai_year"], rng, iterations)
    monitoring = _sample(dists["monitoring_year"], rng, iterations)
    c_var = _sample(dists["c_var_per_claim"], rng, iterations)
    rule_maint = _sample(dists["rule_maintenance_year"], rng, iterations)
    c0 = _sample(dists["initial_investment"], rng, iterations)

    queue = K * N
    caught_ai = p * N * recall_ai
    caught_rule = p * N * recall_rule
    benefit_ai = caught_ai * loss * eta
    benefit_rule = caught_rule * loss * eta
    fh_ai = np.maximum(queue - caught_ai, 0.0)
    fh_rule = np.maximum(queue - caught_rule, 0.0)
    siu_count = siu_frac * queue
    review_cost = queue * c_bs + siu_count * c_siu           # same queue for both systems
    cskh_cost = queue * c_cskh
    ai_ops = gpu + staff + monitoring + c_var * N
    rule_ops = rule_maint

    nv_ai = benefit_ai - review_cost - cskh_cost - fh_ai * dq * v_kh - ai_ops
    nv_rule = benefit_rule - review_cost - cskh_cost - fh_rule * dq * v_kh - rule_ops
    dnv = nv_ai - nv_rule

    annuity = sum(1.0 / (1 + r) ** t for t in range(1, horizon + 1))
    npv = -c0 + dnv * annuity
    roi = npv / c0
    # Discounted payback period via the annuity inversion; inf when never recovered.
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = 1 - c0 * r / dnv
        dpp = np.where((dnv > c0 * r), -np.log(ratio) / np.log(1 + r), np.inf)

    def summ(x):
        finite = x[np.isfinite(x)]
        return {"mean": float(np.mean(finite)), "median": float(np.median(finite)),
                "p5": float(np.quantile(finite, 0.05)), "p95": float(np.quantile(finite, 0.95))}

    crit = cfg["decision_criteria"]
    return {
        "iterations": iterations,
        "structural": {"N": N, "discount_rate": r, "horizon_years": horizon, "siu_rate_within_queue": siu_frac},
        "recall_real": {"ai": summ(recall_ai), "rule": summ(recall_rule), "delta": summ(recall_ai - recall_rule)},
        "nv_ai_annual": summ(nv_ai), "nv_rule_annual": summ(nv_rule), "dnv_annual": summ(dnv),
        "npv": summ(npv), "roi": summ(roi),
        "dpp_years": {"median": float(np.median(dpp[np.isfinite(dpp)])) if np.isfinite(dpp).any() else float("inf"),
                      "p5": float(np.quantile(dpp[np.isfinite(dpp)], 0.05)) if np.isfinite(dpp).any() else float("inf"),
                      "p95": float(np.quantile(dpp[np.isfinite(dpp)], 0.95)) if np.isfinite(dpp).any() else float("inf"),
                      "prob_never_recovered": float(np.mean(~np.isfinite(dpp)))},
        "probabilities": {
            "delta_nv_positive": float(np.mean(dnv > crit["delta_nv_positive"])),
            "npv_positive": float(np.mean(npv > crit["npv_positive"])),
            "dpp_within_horizon": float(np.mean(dpp <= crit["dpp_max_years"])),
        },
        "_draws": {"npv": npv, "dnv": dnv, "roi": roi, "dpp": dpp},
    }
