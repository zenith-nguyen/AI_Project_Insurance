"""Run one PaddleOCR candidate on the private Vietnamese validation manifest."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document.ocr import PaddleOCREngine
from src.document.ocr_benchmark import load_ground_truth, sha256_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Private prediction JSONL path")
    parser.add_argument("--lang", default="vi")
    parser.add_argument("--profile", choices=("robust", "fast_upright"), default="robust")
    parser.add_argument("--max-side", type=int)
    parser.add_argument("--resume", action="store_true", help="Continue a matching interrupted run")
    parser.add_argument("--force", action="store_true", help="Replace an existing candidate run")
    return parser.parse_args()


def _metadata_path(output: Path) -> Path:
    return output.with_name(output.name + ".run.json")


def _read_completed(output: Path) -> set[str]:
    completed: set[str] = set()
    if not output.is_file():
        return completed
    for line_number, line in enumerate(output.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Prediction output is truncated on line {line_number}; remove the last line and resume") from error
        sample_id = str(row.get("sample_id", ""))
        if not sample_id or sample_id in completed:
            raise ValueError(f"Duplicate or empty sample_id in existing predictions: {sample_id!r}")
        completed.add(sample_id)
    return completed


def _run_contract(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": "vietnamese_ocr_candidate_run_v1",
        "manifest_sha256": sha256_file(args.manifest),
        "lang": args.lang,
        "profile": args.profile,
        "max_side": args.max_side,
    }


def _prepare_run(args: argparse.Namespace) -> tuple[dict[str, Any], set[str]]:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = _metadata_path(args.output)
    contract = _run_contract(args)
    if args.force:
        args.output.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
    if args.output.exists() and not args.resume:
        raise FileExistsError("Prediction output exists; use --resume or --force")
    if args.resume and args.output.exists():
        if not metadata_path.is_file():
            raise FileNotFoundError("Resume metadata is missing; use --force for a new run")
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        for key, expected in contract.items():
            if existing.get(key) != expected:
                raise ValueError(f"Cannot resume because {key} changed")
    else:
        metadata_path.write_text(
            json.dumps({**contract, "started_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return contract, _read_completed(args.output)


def main() -> None:
    args = parse_args()
    if args.max_side is not None and args.max_side < 640:
        raise ValueError("--max-side must be at least 640")
    rows = load_ground_truth(args.manifest)
    contract, completed = _prepare_run(args)
    engine = PaddleOCREngine(lang=args.lang, profile=args.profile, max_side=args.max_side)
    pending = [row for row in rows if row["sample_id"] not in completed]
    print(f"Candidate: {engine.model_version}; completed={len(completed)}; pending={len(pending)}", flush=True)
    with args.output.open("a", encoding="utf-8", newline="\n") as stream:
        for index, row in enumerate(pending, start=1):
            started = time.perf_counter()
            tokens = engine.predict(Path(row["resolved_image_path"]))
            latency = time.perf_counter() - started
            prediction = {
                "sample_id": row["sample_id"],
                "predicted_text": "\n".join(token.text for token in tokens),
                "latency_seconds": round(latency, 4),
                "token_count": len(tokens),
                "model_version": engine.model_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            stream.write(json.dumps(prediction, ensure_ascii=False) + "\n")
            stream.flush()
            print(
                f"[{len(completed) + index}/{len(rows)}] {row['sample_id']}: {latency:.1f}s, {len(tokens)} token(s)",
                flush=True,
            )
    metadata_path = _metadata_path(args.output)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        **contract,
        "status": "completed",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "prediction_rows": len(rows),
        "prediction_sha256": sha256_file(args.output),
        "privacy": "Prediction text is private and must not be committed to Git.",
    })
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Completed: {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
