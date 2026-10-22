"""Monte Carlo ROI for the review operating point (t1, t2).

Two-queue model: a claim with score >= t1 enters manual review; score >= t2 is
escalated to SIU, which investigates deeper and prevents a larger share of the
loss at a higher cost. Fraud loss avoided, prevention effectiveness and per-claim
costs are declared as probability distributions (Beta / log-normal / uniform) and
drawn by Monte Carlo. Rates under a target prevalence come from the frozen
class-conditional score distributions (label shift), so results are scenarios
conditioned on declared assumptions, never measured business outcomes.

All money is VND. The assumptions are placeholders until the cost owner confirms
real, sourced figures.
"""
from __future__ import annotations

import math

import numpy as np


# ---- parameter distributions -------------------------------------------------

def sample_param(spec: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    dist = spec["dist"]
    if dist == "lognormal":
        return float(spec["median"]) * np.exp(float(spec["sigma"]) * rng.standard_normal(n))
    if dist == "beta":
        return rng.beta(float(spec["alpha"]), float(spec["beta"]), n)
    if dist == "uniform":
        return rng.uniform(float(spec["low"]), float(spec["high"]), n)
    raise ValueError(f"Unsupported distribution: {dist}")


def mean_param(spec: dict) -> float:
    dist = spec["dist"]
    if dist == "lognormal":
        return float(spec["median"]) * math.exp(float(spec["sigma"]) ** 2 / 2)
    if dist == "beta":
        return float(spec["alpha"]) / (float(spec["alpha"]) + float(spec["beta"]))
    if dist == "uniform":
        return (float(spec["low"]) + float(spec["high"])) / 2
    raise ValueError(f"Unsupported distribution: {dist}")


# ---- queue rates under a target prevalence (label shift) ---------------------

def _survival(class_scores: np.ndarray, threshold: float) -> float:
    """P(score >= threshold) within one class, from its frozen score sample."""
    if len(class_scores) == 0:
        return 0.0
    return float(np.mean(class_scores >= threshold))


def queue_rates(pos_scores, neg_scores, t1: float, t2: float, prevalence: float) -> dict:
    """Per-claim expected rates at (t1, t2) under the assumed prevalence.

    caught_manual / caught_siu are fraud (positive) fractions of the whole
    portfolio; reviewed/siu/false_holds are per-claim rates for costing.
    """
    if not t2 >= t1:
        raise ValueError("t2 must be >= t1 (SIU threshold is stricter)")
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    p = float(prevalence)
    rp1, rp2 = _survival(pos, t1), _survival(pos, t2)
    rn1, rn2 = _survival(neg, t1), _survival(neg, t2)
    return {
        "caught_manual": p * (rp1 - rp2),      # fraud flagged to manual band
        "caught_siu": p * rp2,                 # fraud escalated to SIU
        "reviewed": p * rp1 + (1 - p) * rn1,   # everything in review (manual + SIU)
        "siu": p * rp2 + (1 - p) * rn2,        # everything escalated to SIU
        "false_holds": (1 - p) * rn1,          # legitimate claims flagged
        "total_review_rate": p * rp1 + (1 - p) * rn1,
        "siu_rate": p * rp2 + (1 - p) * rn2,
        "fraud_recall_review": rp1,            # recall among frauds at t1
    }


# ---- net value ---------------------------------------------------------------

def expected_net_value(rates: dict, dists: dict, portfolio: int) -> float:
    """Analytic E[net value] over the assumption distributions (fast, for search)."""
    loss = mean_param(dists["fraud_loss_avoided"])
    eff_m = mean_param(dists["prevention_effectiveness_manual"])
    eff_s = mean_param(dists["prevention_effectiveness_siu"])
    avoided = (rates["caught_manual"] * eff_m + rates["caught_siu"] * eff_s) * loss
    cost = (rates["reviewed"] * mean_param(dists["review_cost"])
            + rates["siu"] * mean_param(dists["siu_cost"])
            + rates["false_holds"] * mean_param(dists["false_hold_cost"])
            + mean_param(dists["ai_operation_cost_per_claim"]))
    return portfolio * (avoided - cost)


def simulate_net_value(rates: dict, dists: dict, portfolio: int, rng: np.random.Generator, iterations: int) -> np.ndarray:
    """Monte Carlo net-value draws (length `iterations`) at one operating point."""
    loss = sample_param(dists["fraud_loss_avoided"], rng, iterations)
    eff_m = sample_param(dists["prevention_effectiveness_manual"], rng, iterations)
    eff_s = sample_param(dists["prevention_effectiveness_siu"], rng, iterations)
    review = sample_param(dists["review_cost"], rng, iterations)
    siu = sample_param(dists["siu_cost"], rng, iterations)
    false_hold = sample_param(dists["false_hold_cost"], rng, iterations)
    ai = sample_param(dists["ai_operation_cost_per_claim"], rng, iterations)
    avoided = (rates["caught_manual"] * eff_m + rates["caught_siu"] * eff_s) * loss
    cost = rates["reviewed"] * review + rates["siu"] * siu + rates["false_holds"] * false_hold + ai
    return portfolio * (avoided - cost)


def summarize(draws: np.ndarray) -> dict:
    return {
        "mean": float(np.mean(draws)),
        "median": float(np.median(draws)),
        "p5": float(np.quantile(draws, 0.05)),
        "p95": float(np.quantile(draws, 0.95)),
        "prob_positive": float(np.mean(draws > 0)),
    }


# ---- operating-point search --------------------------------------------------

def choose_operating_point(pos_scores, neg_scores, dists: dict, prevalence: float,
                           portfolio: int, k1_max: float, k2_max: float, points: int = 160) -> dict:
    """Grid search (t1 <= t2) maximizing analytic E[net value] under K1/K2 caps."""
    grid = np.linspace(float(min(np.min(pos_scores), np.min(neg_scores))),
                       float(max(np.max(pos_scores), np.max(neg_scores))), points)
    best = None
    for t1 in grid:
        rates_t1 = queue_rates(pos_scores, neg_scores, t1, t1, prevalence)
        if rates_t1["total_review_rate"] > k1_max:
            continue
        for t2 in grid[grid >= t1]:
            rates = queue_rates(pos_scores, neg_scores, t1, t2, prevalence)
            if rates["siu_rate"] > k2_max:
                continue
            value = expected_net_value(rates, dists, portfolio)
            if best is None or value > best["expected_net_value"]:
                best = {"t1": float(t1), "t2": float(t2), "expected_net_value": float(value),
                        "total_review_rate": rates["total_review_rate"], "siu_rate": rates["siu_rate"],
                        "fraud_recall_review": rates["fraud_recall_review"]}
    if best is None:
        raise ValueError("No operating point satisfies the K1/K2 constraints")
    return best


def net_value_by_capacity(pos_scores, neg_scores, dists: dict, prevalence: float,
                          portfolio: int, k1_max: float, k2_max: float,
                          rng: np.random.Generator, iterations: int, steps: int = 24) -> list[dict]:
    """Net-value curve vs total review capacity K: for each K, pick the best t2
    (SIU split) under K2 and run Monte Carlo at that (t1, t2)."""
    grid = np.linspace(float(min(np.min(pos_scores), np.min(neg_scores))),
                       float(max(np.max(pos_scores), np.max(neg_scores))), 160)
    curve = []
    for k in np.linspace(0.02, k1_max, steps):
        # t1 giving realized review rate closest to K without exceeding it.
        feasible = [(t, queue_rates(pos_scores, neg_scores, t, t, prevalence)["total_review_rate"]) for t in grid]
        under = [(t, r) for t, r in feasible if r <= k + 1e-9]
        if not under:
            continue
        t1 = min(under, key=lambda tr: k - tr[1])[0]
        # best t2 under K2.
        best = None
        for t2 in grid[grid >= t1]:
            rates = queue_rates(pos_scores, neg_scores, t1, t2, prevalence)
            if rates["siu_rate"] > k2_max:
                continue
            value = expected_net_value(rates, dists, portfolio)
            if best is None or value > best[0]:
                best = (value, t2, rates)
        if best is None:
            continue
        draws = simulate_net_value(best[2], dists, portfolio, rng, iterations)
        stats = summarize(draws)
        curve.append({"capacity_k": float(k), "t1": float(t1), "t2": float(best[1]),
                      "realized_review_rate": best[2]["total_review_rate"],
                      "siu_rate": best[2]["siu_rate"], **stats})
    return curve
