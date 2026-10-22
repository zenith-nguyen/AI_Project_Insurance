"""Audit the B0 rule tie-break at the top-K queue boundary and lock a label-free rule.

The rule baseline emits only a few discrete scores, so many claims tie at the
top-K boundary. The default top-K selection then resolves ties by input row
order, which is arbitrary and makes Recall@K / Precision@K depend on how the
rows happen to be ordered. This script quantifies that swing and compares it
with a locked, label-free tie-break (a sha256 hash of claim_id), which selects
the same claims on every run without touching the label.

Run:
    python scripts/audit_b0_tie_break.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.baselines.rules import RuleBaseline
from src.evaluation.metrics import hash_tiebreaker, precision_at_k, recall_at_k, top_mask

K = 0.10
SPLIT = ROOT / "data/gold/feature_selection_v1/val_fs.parquet"
OUT = ROOT / "reports/phase5/b0_tie_break_audit.json"


def main() -> int:
    frame = pd.read_parquet(SPLIT)
    train = pd.read_parquet(ROOT / "data/gold/feature_selection_v1/train_fs.parquet")
    labels = frame.fraud_label.astype(int).to_numpy()
    scores = RuleBaseline().fit(train).score(frame)

    n = len(frame)
    queue = int(np.ceil(n * K))
    order = np.argsort(-scores, kind="stable")
    boundary = scores[order[queue - 1]]
    tied_at_boundary = int((scores == boundary).sum())
    above_boundary = int((scores > boundary).sum())
    free_seats = queue - above_boundary

    # Current behaviour: original row order breaks ties.
    row_recall = recall_at_k(labels, scores, K)
    row_precision = precision_at_k(labels, scores, K)

    # Locked behaviour: label-free sha256(claim_id) tie-break.
    tb = hash_tiebreaker(frame.claim_id.to_numpy())
    locked_recall = recall_at_k(labels, scores, K, tb)
    locked_precision = precision_at_k(labels, scores, K, tb)

    # How far can the metric swing purely from tie order (random, label-free)?
    rng = np.random.default_rng(20261022)
    recalls = []
    for _ in range(2000):
        jitter = rng.random(n)
        mask = top_mask(scores, K, jitter)
        recalls.append(float(labels[mask].sum() / labels.sum()))
    recalls = np.array(recalls)

    report = {
        "split": SPLIT.name,
        "k": K,
        "n": n,
        "queue_size": queue,
        "boundary_score": float(boundary),
        "claims_tied_at_boundary": tied_at_boundary,
        "seats_above_boundary": above_boundary,
        "free_seats_decided_by_tie_break": int(free_seats),
        "recall_at_k": {
            "row_order_current": row_recall,
            "locked_hash_tiebreak": locked_recall,
            "random_tie_min": float(recalls.min()),
            "random_tie_median": float(np.median(recalls)),
            "random_tie_max": float(recalls.max()),
        },
        "precision_at_k": {
            "row_order_current": row_precision,
            "locked_hash_tiebreak": locked_precision,
        },
        "locked_rule": "secondary key = sha256(claim_id) as float in [0,1); label-free, order-independent, reproducible",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
