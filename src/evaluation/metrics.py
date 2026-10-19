"""Fraud ranking and uncertainty metrics."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def top_mask(scores, k: float) -> np.ndarray:
    values = np.asarray(scores, dtype=float)
    if not 0 < k <= 1 or values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("k must be in (0,1], and scores must be finite 1D values")
    n = max(1, math.ceil(len(values) * k))
    # Stable order resolves equal scores by their original row order.
    chosen = np.argsort(-values, kind="stable")[:n]
    mask = np.zeros(len(values), dtype=bool)
    mask[chosen] = True
    return mask


def recall_at_k(y, scores, k: float) -> float:
    labels = np.asarray(y, dtype=int)
    if labels.sum() == 0:
        return float("nan")
    return float(labels[top_mask(scores, k)].sum() / labels.sum())


def precision_at_k(y, scores, k: float) -> float:
    labels = np.asarray(y, dtype=int)
    return float(labels[top_mask(scores, k)].mean())


def lift_at_k(y, scores, k: float) -> float:
    labels = np.asarray(y, dtype=int)
    return precision_at_k(labels, scores, k) / labels.mean() if labels.mean() else float("nan")


def evaluate(y, scores, k_values=(0.1, 0.2), probability: bool = False) -> dict:
    labels = np.asarray(y, dtype=int)
    values = np.asarray(scores, dtype=float)
    result = {"n": int(len(labels)), "fraud_count": int(labels.sum()), "prevalence": float(labels.mean()), "average_precision": float(average_precision_score(labels, values)), "roc_auc": float(roc_auc_score(labels, values))}
    for k in k_values:
        key = f"at_{int(k * 100)}pct"
        result[f"recall_{key}"] = recall_at_k(labels, values, k)
        result[f"precision_{key}"] = precision_at_k(labels, values, k)
        result[f"lift_{key}"] = lift_at_k(labels, values, k)
    if probability:
        result["brier"] = float(brier_score_loss(labels, values))
        bins = np.minimum((values * 10).astype(int), 9)
        result["ece_10_bins"] = float(sum((bins == index).mean() * abs(labels[bins == index].mean() - values[bins == index].mean()) for index in range(10) if (bins == index).any()))
    return result


def stratified_bootstrap(y, scores, k: float, samples: int = 1000, seed: int = 42) -> dict:
    labels = np.asarray(y, dtype=int)
    values = np.asarray(scores, dtype=float)
    positive, negative = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    if not len(positive) or not len(negative):
        raise ValueError("Bootstrap needs both classes")
    rng = np.random.default_rng(seed)
    functions = {"average_precision": lambda a, b: average_precision_score(a, b), "roc_auc": roc_auc_score, "recall_at_k": lambda a, b: recall_at_k(a, b, k), "precision_at_k": lambda a, b: precision_at_k(a, b, k)}
    draws = {name: [] for name in functions}
    for _ in range(samples):
        indices = np.concatenate([rng.choice(positive, len(positive), replace=True), rng.choice(negative, len(negative), replace=True)])
        rng.shuffle(indices)
        for name, function in functions.items():
            draws[name].append(float(function(labels[indices], values[indices])))
    return {name: {"point": float(function(labels, values)), "lower": float(np.quantile(draws[name], 0.025)), "upper": float(np.quantile(draws[name], 0.975)), "n_bootstrap": samples} for name, function in functions.items()}


def paired_stratified_bootstrap(y, baseline_scores, candidate_scores, k: float, samples: int = 1000, seed: int = 42) -> dict:
    """Paired bootstrap CI for candidate-minus-baseline ranking metrics.

    Both score arrays must describe the same claims in the same order. Reusing
    each stratified resample for both systems preserves the pairing and gives a
    more appropriate uncertainty interval for their difference.
    """
    labels = np.asarray(y, dtype=int)
    baseline = np.asarray(baseline_scores, dtype=float)
    candidate = np.asarray(candidate_scores, dtype=float)
    if labels.ndim != 1 or baseline.shape != labels.shape or candidate.shape != labels.shape:
        raise ValueError("Labels, baseline scores and candidate scores must be aligned 1D arrays")
    if not np.isfinite(baseline).all() or not np.isfinite(candidate).all():
        raise ValueError("Bootstrap scores must be finite")
    positive, negative = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    if not len(positive) or not len(negative):
        raise ValueError("Bootstrap needs both classes")
    rng = np.random.default_rng(seed)
    functions = {
        "average_precision": lambda a, b: average_precision_score(a, b),
        "recall_at_k": lambda a, b: recall_at_k(a, b, k),
        "precision_at_k": lambda a, b: precision_at_k(a, b, k),
    }
    draws = {name: [] for name in functions}
    for _ in range(samples):
        indices = np.concatenate([
            rng.choice(positive, len(positive), replace=True),
            rng.choice(negative, len(negative), replace=True),
        ])
        rng.shuffle(indices)
        for name, function in functions.items():
            draws[name].append(float(function(labels[indices], candidate[indices]) - function(labels[indices], baseline[indices])))
    result = {}
    for name, function in functions.items():
        baseline_point = float(function(labels, baseline))
        candidate_point = float(function(labels, candidate))
        lower, upper = np.quantile(draws[name], [0.025, 0.975])
        result[name] = {
            "baseline": baseline_point,
            "candidate": candidate_point,
            "delta": candidate_point - baseline_point,
            "lower": float(lower),
            "upper": float(upper),
            "contains_zero": bool(lower <= 0 <= upper),
            "n_bootstrap": samples,
        }
    return result
