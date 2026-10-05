"""Frozen validation thresholds and operational action rates."""
from __future__ import annotations

import math

import numpy as np


def _boundary(scores: np.ndarray, share: float) -> float:
    ordered = np.sort(np.asarray(scores, dtype=float))[::-1]
    count = max(1, math.ceil(len(ordered) * share))
    if count >= len(ordered):
        return float("-inf")
    return float((ordered[count - 1] + ordered[count]) / 2)


def choose_thresholds(scores, review_capacity: float, siu_capacity: float) -> dict:
    if not 0 < siu_capacity < review_capacity < 1:
        raise ValueError("Expected 0 < SIU capacity < total review capacity < 1")
    values = np.asarray(scores, dtype=float)
    return {"t1": _boundary(values, review_capacity), "t2": _boundary(values, siu_capacity), "review_capacity_target": review_capacity, "siu_capacity_target": siu_capacity, "tie_policy": "equal boundary scores may exceed capacity; review observed rates"}


def operational_metrics(y, scores, thresholds: dict) -> dict:
    labels, values = np.asarray(y, dtype=int), np.asarray(scores, dtype=float)
    review = values >= thresholds["t1"]
    siu = values >= thresholds["t2"]
    negatives = labels == 0
    positives = labels == 1
    return {"stp_rate": float((~review).mean()), "manual_review_rate": float((review & ~siu).mean()), "siu_rate": float(siu.mean()), "total_review_rate": float(review.mean()), "false_hold_rate": float((review & negatives).sum() / negatives.sum()), "queue_false_alarm_rate": float(1 - labels[review].mean()) if review.any() else None, "fraud_recall_review_queue": float((review & positives).sum() / positives.sum())}
