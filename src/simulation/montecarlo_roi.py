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


def recall_shift_binormal(recall_test: float, prevalence_test: float, prevalence_target: float, k: float = 0.10) -> float:
    """Convert a Recall@k measured at one prevalence to another via an equal-variance
    binormal model (group B ~ N(d, 1), group A ~ N(0, 1)).

    Reproduces Thanh Vy's worked example: a test Recall@10% of 0.224 at p=0.245 maps to
    ~0.285 at p=0.07. Do NOT infer d from ROC-AUC; fit it to the observed head-of-list
    recall instead. Recall is capped at min(1, k/prevalence).
    """
    import math

    def sf(x):
        return 0.5 * math.erfc(x / math.sqrt(2))

    def tau(d, p):
        lo, hi = -12.0, 12.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if p * sf(mid - d) + (1 - p) * sf(mid) - k > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def recall(d, p):
        return sf(tau(d, p) - d)

    target = min(max(recall_test, 1e-6), min(1.0, k / prevalence_test) - 1e-9)
    lo, hi = 0.0, 8.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if recall(mid, prevalence_test) < target:
            lo = mid
        else:
            hi = mid
    d = (lo + hi) / 2
    return min(recall(d, prevalence_target), min(1.0, k / prevalence_target))


def _dist_means(dists: dict) -> dict:
    return {key: mean_param(spec) for key, spec in dists.items()}


def _best_point_grid(pos_sorted, neg_sorted, means: dict, prevalence: float, portfolio: int,
                     k1_max: float, k2_max: float, grid: np.ndarray):
    """Vectorized operating-point search over a (t1, t2) grid. Returns a dict or None."""
    p = float(prevalence)
    def survival(sorted_scores, g):
        idx = np.searchsorted(sorted_scores, g, side="left")
        return (len(sorted_scores) - idx) / len(sorted_scores)
    rp, rn = survival(pos_sorted, grid), survival(neg_sorted, grid)
    rp_i, rp_j = rp[:, None], rp[None, :]
    rn_i, rn_j = rn[:, None], rn[None, :]
    caught_m = p * (rp_i - rp_j)
    caught_s = p * rp_j
    reviewed = p * rp_i + (1 - p) * rn_i                 # depends on t1 (row)
    siu = p * rp_j + (1 - p) * rn_j                       # depends on t2 (col)
    false_holds = (1 - p) * rn_i
    avoided = (caught_m * means["prevention_effectiveness_manual"]
               + caught_s * means["prevention_effectiveness_siu"]) * means["fraud_loss_avoided"]
    cost = (reviewed * means["review_cost"] + siu * means["siu_cost"]
            + false_holds * means["false_hold_cost"] + means["ai_operation_cost_per_claim"])
    nv = portfolio * (avoided - cost)
    feasible = (grid[None, :] >= grid[:, None]) & (reviewed <= k1_max) & (siu <= k2_max)
    nv = np.where(feasible, nv, -np.inf)
    if not np.isfinite(nv).any():
        return None
    i, j = np.unravel_index(int(np.argmax(nv)), nv.shape)
    review_rate = float((p * rp[i] + (1 - p) * rn[i]))
    siu_rate = float((p * rp[j] + (1 - p) * rn[j]))
    return {"t1": float(grid[i]), "t2": float(grid[j]), "expected_net_value": float(nv[i, j]),
            "total_review_rate": review_rate, "siu_rate": siu_rate}


def bootstrap_operating_point(pos_scores, neg_scores, dists: dict, prevalence: float, portfolio: int,
                              k1_max: float, k2_max: float, rng: np.random.Generator,
                              n_boot: int = 300, grid_points: int = 80, inner: int = 20) -> dict:
    """Resample the validation scores to show how unstable (t1, t2) and net value are
    given the small validation set, combined with the cost Monte Carlo."""
    pos = np.asarray(pos_scores, float)
    neg = np.asarray(neg_scores, float)
    means = _dist_means(dists)
    lo = float(min(pos.min(), neg.min()))
    hi = float(max(pos.max(), neg.max()))
    grid = np.linspace(lo, hi, grid_points)
    t1s, t2s, reviews, combined = [], [], [], []
    for _ in range(n_boot):
        pb = np.sort(pos[rng.integers(0, len(pos), len(pos))])
        nb = np.sort(neg[rng.integers(0, len(neg), len(neg))])
        best = _best_point_grid(pb, nb, means, prevalence, portfolio, k1_max, k2_max, grid)
        if best is None:
            continue
        t1s.append(best["t1"]); t2s.append(best["t2"]); reviews.append(best["total_review_rate"])
        rates = queue_rates(pos, neg, best["t1"], best["t2"], prevalence)  # score at that point on full sample
        combined.extend(simulate_net_value(rates, dists, portfolio, rng, inner).tolist())
    combined = np.asarray(combined)
    return {
        "n_boot": len(t1s),
        "t1": {"median": float(np.median(t1s)), "p5": float(np.quantile(t1s, 0.05)), "p95": float(np.quantile(t1s, 0.95))},
        "t2": {"median": float(np.median(t2s)), "p5": float(np.quantile(t2s, 0.05)), "p95": float(np.quantile(t2s, 0.95))},
        "review_rate": {"median": float(np.median(reviews)), "p5": float(np.quantile(reviews, 0.05)), "p95": float(np.quantile(reviews, 0.95))},
        "net_value": summarize(combined),
        "_draws": combined,
        "_t1_samples": np.asarray(t1s),
    }


def fixed_point_regret(pos_scores, neg_scores, dists: dict, t1: float, t2: float,
                       prevalences, portfolio: int, k1_max: float, k2_max: float) -> list[dict]:
    """Expected-net-value regret of deploying one fixed (t1, t2) vs re-optimizing per prevalence."""
    out = []
    for prevalence in prevalences:
        fixed_rates = queue_rates(pos_scores, neg_scores, t1, t2, prevalence)
        fixed_nv = expected_net_value(fixed_rates, dists, portfolio)
        # The fixed point may exceed capacity at a different prevalence; flag it, since a
        # negative regret only means the fixed point would breach the K1/K2 caps there.
        feasible = fixed_rates["total_review_rate"] <= k1_max + 1e-9 and fixed_rates["siu_rate"] <= k2_max + 1e-9
        oracle = choose_operating_point(pos_scores, neg_scores, dists, prevalence, portfolio, k1_max, k2_max)
        out.append({"prevalence": float(prevalence), "fixed_net_value": fixed_nv,
                    "fixed_feasible": bool(feasible),
                    "oracle_net_value": oracle["expected_net_value"],
                    "regret": oracle["expected_net_value"] - fixed_nv,
                    "regret_pct": (oracle["expected_net_value"] - fixed_nv) / oracle["expected_net_value"] if oracle["expected_net_value"] else 0.0})
    return out


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
