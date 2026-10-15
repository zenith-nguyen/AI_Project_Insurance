"""Validate a private Vietnamese OCR benchmark and produce an aggregate report."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document.ocr_benchmark import evaluate_ocr, load_ground_truth, load_predictions, sha256_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="Private ground-truth JSONL manifest")
    parser.add_argument("--predictions", type=Path, required=True, help="OCR predictions JSONL")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate JSON report path")
    parser.add_argument("--minimum-pages", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.minimum_pages < 1:
        raise ValueError("--minimum-pages must be positive")
    ground_truth = load_ground_truth(args.manifest)
    predictions = load_predictions(args.predictions)
    report = evaluate_ocr(ground_truth, predictions, minimum_pages=args.minimum_pages)
    report.update({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256_file(args.manifest),
        "predictions_sha256": sha256_file(args.predictions),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": report["gate"]["passed"],
        "pages": report["overall"]["pages"],
        "cer": report["overall"]["cer"],
        "wer": report["overall"]["wer"],
        "exact_match_rate": report["overall"]["exact_match_rate"],
        "latency_p95_seconds": report["latency_seconds"]["p95"],
        "output": str(args.output.resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
