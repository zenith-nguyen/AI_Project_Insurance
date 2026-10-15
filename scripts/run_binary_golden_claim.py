"""Run one isolated binary golden claim through the same API used by the UI.

This is an engineering integration check. The bundled image and document are
synthetic, so a PASS proves orchestration, traceability and fallback behavior;
it does not prove model accuracy on Vietnamese insurance data.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STRICT_MODULES = {
    "tabular_risk", "consistency", "relationships", "media_authenticity",
    "damage_segmentation", "document_pipeline",
}


def evaluate_gate(analysis: dict, events: list[dict]) -> dict:
    statuses = analysis.get("module_status", {})
    module_pass = {
        name: statuses.get(name, {}).get("status") == "completed"
        for name in sorted(STRICT_MODULES)
    }
    evidence_kinds = {item.get("kind") for item in analysis.get("evidence", [])}
    return {
        "module_pass": module_pass,
        "binary_image_reached_analysis": "image" in evidence_kinds,
        "binary_document_reached_analysis": "document" in evidence_kinds,
        "analysis_traceable": bool(analysis.get("trace_id") and analysis.get("model_versions")),
        "audit_replay_pass": {item.get("event_type") for item in events} >= {"review", "field_correction"},
        "passed": all(module_pass.values())
        and "image" in evidence_kinds
        and "document" in evidence_kinds
        and bool(analysis.get("trace_id") and analysis.get("model_versions"))
        and {item.get("event_type") for item in events} >= {"review", "field_correction"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/metrics/golden_binary_integration_v1.json")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    claim_id = f"CLM-GOLD-BINARY-{run_id}"
    runtime_root = ROOT / "runtime/golden_binary_runs" / run_id / "claims"
    os.environ["INSURANCE_API_MODE"] = "live"
    os.environ["INSURANCE_RUNTIME_CLAIM_ROOT"] = str(runtime_root)
    os.environ["INSURANCE_AUDIT_LOG"] = str(runtime_root.parent / "audit.jsonl")
    os.environ.setdefault("INSURANCE_YOLO_WEIGHTS", str(ROOT / "artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt"))
    os.environ.setdefault("INSURANCE_LAYOUTLM_CHECKPOINT", str(ROOT / "artifacts/models/document_kie/layoutlmv3_sroie_candidate_v2/checkpoint-264"))

    from fastapi.testclient import TestClient
    from src.api.app import app

    golden_root = ROOT / "data/golden/claims/CLM-GOLD-001"
    golden = json.loads((golden_root / "claim.json").read_text(encoding="utf-8"))
    image = ROOT / "prototype/demo_assets/synthetic_vehicle_collision.png"
    document = ROOT / "prototype/demo_assets/synthetic_repair_estimate.png"
    for path in (image, document):
        if not path.is_file():
            raise FileNotFoundError(path)

    started = time.perf_counter()
    with TestClient(app) as client:
        readiness = client.get("/readiness").json()
        intake = {
            "claim_amount": golden["claim_amount"],
            "incident_date": golden["incident_date"],
            "plate_number": golden["plate_number"],
            "tabular_features": golden["tabular_features"],
            "required_evidence": ["claim-intake", "vehicle_image", "claim_document", "relationship-graph"],
            "relationship_entities": {"contact_phone": "0909000111", "repair_shop": "GARAGE-DEMO-01"},
        }
        response = client.post(f"/claims/{claim_id}/intake", json=intake)
        response.raise_for_status()
        for kind, path in (("image", image), ("document", document)):
            with path.open("rb") as stream:
                response = client.post(
                    f"/claims/{claim_id}/evidence", data={"kind": kind},
                    files={"file": (path.name, stream, "image/png")},
                )
            response.raise_for_status()

        analyze_started = time.perf_counter()
        response = client.post(f"/claims/{claim_id}/analyze", json={})
        response.raise_for_status()
        analysis = response.json()
        analyze_seconds = time.perf_counter() - analyze_started

        response = client.post(
            f"/claims/{claim_id}/review",
            json={"reviewer_id": "golden-runner", "decision": "special_review", "reason": "Synthetic integration sign-off exercise"},
        )
        response.raise_for_status()
        response = client.post(
            f"/claims/{claim_id}/corrections",
            json={
                "reviewer_id": "golden-runner", "document_id": "synthetic_repair_estimate",
                "field_name": "total_amount", "original_value": None, "corrected_value": "61620000",
                "reason": "Synthetic audit replay exercise",
            },
        )
        response.raise_for_status()
        events = client.get(f"/claims/{claim_id}/events").json()

    gate = evaluate_gate(analysis, events)
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "claim_id": claim_id,
        "data_scope": "synthetic_binary_integration_only",
        "accuracy_claim_allowed": False,
        "readiness": readiness,
        "latency_seconds": {"analysis": analyze_seconds, "total": time.perf_counter() - started},
        "analysis": {
            "status": analysis.get("analysis_status"),
            "priority": analysis.get("priority"),
            "trace_id": analysis.get("trace_id"),
            "module_status": analysis.get("module_status"),
            "model_versions": analysis.get("model_versions"),
            "signal_count": len(analysis.get("signals", [])),
            "damage_region_count": len(analysis.get("extracted_fields", {}).get("damage_detections", [])),
            "document_result_count": len(analysis.get("extracted_fields", {}).get("document_results", [])),
        },
        "gate": gate,
        "limitations": [
            "Synthetic evidence validates integration, not domain accuracy.",
            "Research handoff still requires 20–50 signed golden claims.",
            "Vietnamese insurance-domain validation and business UAT remain open.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not gate["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
