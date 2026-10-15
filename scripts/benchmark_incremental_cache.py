"""Verify per-evidence reuse after a new file is added to an analyzed claim."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_demo_v2 import CASES, SAMPLE_FEATURES, _request, find_pack, upload, wait_job


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pack-root", type=Path)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / f"runtime/benchmarks/incremental_evidence_cache_{datetime.now().date().isoformat()}.json",
    )
    parser.add_argument("--timeout-seconds", type=float, default=600)
    args = parser.parse_args()
    pack = (args.pack_root or find_pack()).resolve()
    first, second = CASES[0], CASES[1]
    claim_id = f"CLM-CACHE-{datetime.now(timezone.utc):%m%d%H%M%S}-{uuid4().hex[:5]}"
    intake = {
        "claim_amount": first["amount"], "incident_date": first["date"],
        "plate_number": first["plate"], "tabular_features": SAMPLE_FEATURES,
        "relationship_entities": {"contact_phone": first["phone"], "repair_shop": first["garage"]},
        "required_evidence": ["claim-intake", "vehicle_image", "claim_document", "relationship-graph"],
    }
    with httpx.Client(
        base_url=args.base_url, timeout=60,
        limits=httpx.Limits(max_keepalive_connections=0),
    ) as client:
        _request(client, "POST", f"/claims/{claim_id}/intake", json=intake)
        upload(client, claim_id, "image", pack / first["folder"] / first["image"])
        upload(client, claim_id, "document", pack / first["folder"] / first["document"])
        started = time.perf_counter()
        initial = wait_job(
            client, claim_id,
            _request(client, "POST", f"/claims/{claim_id}/analysis-jobs", json={}),
            args.timeout_seconds,
        )
        initial_wall = round(time.perf_counter() - started, 1)

        upload(client, claim_id, "image", pack / second["folder"] / second["image"])
        started = time.perf_counter()
        incremental = wait_job(
            client, claim_id,
            _request(client, "POST", f"/claims/{claim_id}/analysis-jobs", json={}),
            args.timeout_seconds,
        )
        incremental_wall = round(time.perf_counter() - started, 1)
        analysis = _request(client, "GET", f"/claims/{claim_id}/analysis")

    document_status = analysis["module_status"]["document_pipeline"]
    damage_status = analysis["module_status"]["damage_segmentation"]
    checks = {
        "unchanged_document_reused": document_status.get("evidence_cache_hits") == 1,
        "old_image_reused": damage_status.get("evidence_cache_hits") == 1,
        "two_images_processed": damage_status.get("evidence_processed") == 2,
        "ocr_not_repeated": "document_ocr" not in incremental.get("stage_durations_seconds", {}),
        "kie_not_repeated": "document_kie" not in incremental.get("stage_durations_seconds", {}),
    }
    report = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_id": claim_id, "scope": "synthetic_incremental_cache_benchmark",
        "initial": {"job": initial, "wall_seconds": initial_wall},
        "incremental": {"job": incremental, "wall_seconds": incremental_wall},
        "module_status": {
            "document_pipeline": document_status,
            "damage_segmentation": damage_status,
        },
        "checks": checks, "passed": all(checks.values()),
        "business_meaning": (
            "Adding one new image reuses unchanged document and image outputs; "
            "only the new evidence requires model inference."
        ),
        "limitations": [
            "Synthetic runtime benchmark, not a model-accuracy evaluation.",
            "Timing applies to the current machine and active model versions.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "claim_id": claim_id, "initial_seconds": initial["elapsed_seconds"],
        "incremental_seconds": incremental["elapsed_seconds"],
        "checks": checks, "passed": report["passed"], "report": str(args.output.resolve()),
    }, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
