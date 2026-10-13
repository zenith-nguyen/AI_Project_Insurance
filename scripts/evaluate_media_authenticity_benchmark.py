"""Evaluate frozen media-authenticity scores without changing the threshold.

Input JSONL rows must contain: label, split, source_group and score. The two
AI classes are positive. Reported metrics are for triage research, not proof of
fraud or image origin.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


AI_LABELS = {"ai_generated", "ai_edited"}


def evaluate(path: Path, threshold: float, split: str = "test") -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [row for row in rows if row.get("split") == split]
    if not selected:
        raise ValueError(f"No rows found for split={split!r}.")
    tp = fp = tn = fn = 0
    by_label: dict[str, Counter] = defaultdict(Counter)
    for row in selected:
        actual = row["label"] in AI_LABELS
        predicted = float(row["score"]) >= threshold
        outcome = "tp" if actual and predicted else "fn" if actual else "fp" if predicted else "tn"
        by_label[row["label"]][outcome] += 1
        tp += outcome == "tp"
        fp += outcome == "fp"
        tn += outcome == "tn"
        fn += outcome == "fn"
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "valid": True, "split": split, "threshold": threshold, "rows": len(selected),
        "source_groups": len({row["source_group"] for row in selected}),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "by_label": {label: dict(counts) for label, counts in sorted(by_label.items())},
        "policy": "Threshold must be selected on validation and used unchanged on test.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.predictions, args.threshold, args.split)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
