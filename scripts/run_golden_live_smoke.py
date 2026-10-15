"""Run the registered live service over every golden claim and save evidence.

This exercises the same FastAPI route used by the UI. Missing optional model
artifacts are reported by each module; they do not hide the working core slice.
Use ``--require-all`` on a multimodal integration machine to fail unless every
registered model is ready and completes from binary input for every golden
claim. Precomputed document fields never satisfy this strict gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/core_live_smoke.json")
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()

    os.environ["INSURANCE_API_MODE"] = "live"
    yolo = ROOT / "artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt"
    layout = ROOT / "artifacts/models/document_kie/layoutlmv3_sroie_candidate_v2/checkpoint-264"
    if yolo.is_file():
        os.environ.setdefault("INSURANCE_YOLO_WEIGHTS", str(yolo))
    if layout.is_dir():
        os.environ.setdefault("INSURANCE_LAYOUTLM_CHECKPOINT", str(layout))
    from fastapi.testclient import TestClient
    from src.api.app import app

    report: dict[str, object] = {"health": None, "readiness": None, "claims": []}
    with TestClient(app) as client:
        report["health"] = client.get("/health").json()
        readiness_response = client.get("/readiness")
        readiness_response.raise_for_status()
        report["readiness"] = readiness_response.json()

        claim_roots = sorted((ROOT / "data/golden/claims").glob("CLM-*"))
        for claim_root in claim_roots:
            claim_id = claim_root.name
            response = client.post(f"/claims/{claim_id}/analyze", json={})
            item: dict[str, object] = {"claim_id": claim_id, "http_status": response.status_code}
            if response.status_code == 200:
                body = response.json()
                item.update(
                    analysis_status=body.get("analysis_status"),
                    research_risk_score=body.get("research_risk_score"),
                    priority=body.get("priority"),
                    module_status=body.get("module_status"),
                    signal_count=len(body.get("signals", [])),
                )
            else:
                item["error"] = response.text
            report["claims"].append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    claims = report["claims"]
    core_ok = bool(claims) and all(item["http_status"] == 200 for item in claims)
    readiness = report["readiness"]
    strict_modules = {
        "tabular_risk", "consistency", "relationships", "media_authenticity",
        "damage_segmentation", "document_pipeline",
    }
    strict_claims_ok = bool(claims) and all(
        all(item.get("module_status", {}).get(name, {}).get("status") == "completed" for name in strict_modules)
        for item in claims
    )
    all_ok = core_ok and bool(readiness.get("fully_live")) and strict_claims_ok
    report["gate"] = {
        "core_http_ok": core_ok,
        "runtime_models_ready": bool(readiness.get("fully_live")),
        "strict_binary_modules_completed": strict_claims_ok,
        "strict_required_modules": sorted(strict_modules),
        "passed": all_ok if args.require_all else core_ok,
        "note": "completed_precomputed is intentionally rejected by the strict multimodal gate.",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not core_ok or (args.require_all and not all_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
