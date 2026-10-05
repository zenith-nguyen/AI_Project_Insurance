"""Label-shift scenarios from frozen class-conditional score distributions."""
from __future__ import annotations

import numpy as np


def scenario_at_k(y, scores, prevalence: float, k: float) -> dict:
    labels = np.asarray(y, dtype=int)
    values = np.asarray(scores, dtype=float)
    if not 0 < prevalence < 1 or not 0 < k <= 1 or labels.sum() in (0, len(labels)):
        raise ValueError("Both classes and valid prevalence/capacity are required")
    order = np.argsort(-values, kind="stable")
    labels = labels[order]
    weights = np.where(labels == 1, prevalence / labels.sum(), (1 - prevalence) / (len(labels) - labels.sum()))
    cumulative = np.cumsum(weights)
    before = np.concatenate(([0.0], cumulative[:-1]))
    fraction = np.clip((k - before) / weights, 0, 1)
    selected_positive_mass = float(np.sum(weights * labels * fraction))
    return {"assumed_prevalence": prevalence, "capacity": k, "recall_at_k": selected_positive_mass / prevalence, "precision_at_k": selected_positive_mass / k, "assumption": "class-conditional score distributions unchanged"}
