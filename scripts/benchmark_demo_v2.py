"""Benchmark the three synthetic v2 demo claims through the live HTTP API.

The report measures orchestration and latency on the current machine. It is not
an accuracy benchmark and must not be presented as Vietnamese-domain model
validation.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKS = [
    Path(r"D:\My Dowload\Practive_00_DEMO_LOP_MOI_3_HO_SO_2026-10-15_v2"),
    Path(r"D:\My Dowload\00_DEMO_LOP_MOI_3_HO_SO_2026-10-15_v2"),
]

SAMPLE_FEATURES = {
    "months_as_customer": 166, "age": 37, "policy_number": 900001,
    "policy_bind_date": "2008-06-19", "policy_state": "IL", "policy_csl": "100/300",
    "policy_deductable": 2000, "policy_annual_premium": 1337.28, "umbrella_limit": 8000000,
    "insured_zip": 700001, "insured_sex": "MALE", "insured_education_level": "JD",
    "insured_occupation": "craft-repair", "insured_hobbies": "reading",
    "insured_relationship": "husband", "capital_gains": 27500, "capital_loss": 0,
    "incident_date": "2015-02-28", "incident_type": "Multi-vehicle Collision",
    "collision_type": "Side Collision", "incident_severity": "Major Damage",
    "authorities_contacted": "Police", "incident_state": "WV", "incident_city": "Riverwood",
    "incident_location": "Synthetic benchmark location", "incident_hour_of_the_day": 10,
    "number_of_vehicles_involved": 3, "property_damage": "NO", "bodily_injuries": 2,
    "witnesses": 2, "police_report_available": None, "total_claim_amount": 67140,
    "injury_claim": 7460, "property_claim": 7460, "vehicle_claim": 52220,
    "auto_make": "Ford", "auto_model": "F150", "auto_year": 2006,
}

CASES = [
    {
        "key": "hatchback_full", "folder": "01_HATCHBACK_CAM_HO_SO_DAY_DU",
        "image": "01_ANH_XE_HATCHBACK_CAM.png", "document": "02_BAO_GIA_SUA_CHUA.png",
        "amount": 31_600_000, "date": "2026-10-09", "plate": "59H-246.81",
        "phone": "0936221100", "garage": "GARAGE-METRO-21",
    },
    {
        "key": "van_relationship", "folder": "02_VAN_TRANG_DOI_XE_CO_QUAN_HE",
        "image": "01_ANH_XE_VAN_TRANG.png", "document": "02_BIEN_BAN_DOI_XE.png",
        "amount": 24_900_000, "date": "2026-10-10", "plate": "50D-615.37",
        "phone": "0936221100", "garage": "GARAGE-METRO-21",
    },
    {
        "key": "sedan_authenticity", "folder": "03_SEDAN_XANH_DEN_NGUON_GOC_CAN_XEM",
        "image": "01_ANH_XE_CO_KHAI_BAO_AI.png", "document": "02_PHIEU_KIEM_TRA_SO_BO.png",
        "amount": 36_750_000, "date": "2026-10-11", "plate": "61A-904.26",
        "phone": "0984332277", "garage": "GARAGE-LAKE-05",
    },
]
EXPECTED_FIELDS = {
    "hatchback_full": {"document_date": "2026-10-09", "total_amount": 31_600_000.0, "plate_number": "59H24681"},
    "van_relationship": {"document_date": "2026-10-10", "total_amount": 24_900_000.0, "plate_number": "50D61537"},
    "sedan_authenticity": {"document_date": "2026-10-11", "total_amount": 36_750_000.0, "plate_number": "61A90426"},
}


def find_pack() -> Path:
    for path in DEFAULT_PACKS:
        if path.is_dir():
            return path
    raise FileNotFoundError("Không tìm thấy bộ demo v2; truyền --pack-root để chỉ định thư mục.")


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    attempts = 5 if method.upper() == "GET" else 1
    for attempt in range(attempts):
        try:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TransportError:
            if attempt + 1 >= attempts:
                raise
            # Heavy CPU inference can make the Windows development server close
            # an idle keep-alive socket. The job continues; reconnect and poll.
            time.sleep(min(2.0, 0.25 * (2**attempt)))
    raise AssertionError("unreachable")


def upload(client: httpx.Client, claim_id: str, kind: str, path: Path) -> dict:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as stream:
        return _request(
            client, "POST", f"/claims/{claim_id}/evidence", data={"kind": kind},
            files={"file": (path.name, stream, media_type)},
        )


def wait_job(client: httpx.Client, claim_id: str, job: dict, timeout_seconds: float) -> dict:
    deadline = time.monotonic() + timeout_seconds
    previous_stage = None
    while job["status"] in {"queued", "running"}:
        if job["stage"] != previous_stage:
            print(f"  {job['stage']}: {job['message']}", flush=True)
            previous_stage = job["stage"]
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Job {job['job_id']} vượt quá {timeout_seconds:.0f} giây")
        time.sleep(1)
        job = _request(client, "GET", f"/claims/{claim_id}/analysis-jobs/{job['job_id']}")
    if job["status"] != "completed":
        raise RuntimeError(job.get("error") or f"Job kết thúc ở trạng thái {job['status']}")
    return job


def evaluate_business(case_key: str, analysis: dict) -> dict:
    evidence_kinds = {row.get("kind") for row in analysis.get("evidence", [])}
    statuses = analysis.get("module_status", {})
    required_modules = {
        "tabular_risk", "media_authenticity", "damage_segmentation",
        "document_pipeline", "consistency", "relationships",
    }
    checks = {
        "image_and_document_received": {"image", "document"}.issubset(evidence_kinds),
        "required_modules_completed": all(statuses.get(name, {}).get("status") == "completed" for name in required_modules),
        "traceability_present": bool(analysis.get("trace_id") and analysis.get("model_versions")),
    }
    recovered = {}
    for document in analysis.get("extracted_fields", {}).get("document_results", []):
        for field in document.get("fields", []):
            recovered[field.get("field_name")] = field.get("normalized_value")
    expected = EXPECTED_FIELDS.get(case_key, {})
    checks["critical_document_fields_recovered"] = all(recovered.get(name) == value for name, value in expected.items())
    if case_key == "van_relationship":
        checks["relationship_found"] = bool(analysis.get("graph_features", {}).get("related_claim_ids"))
    if case_key == "sedan_authenticity":
        checks["authenticity_review_signal"] = any(
            row.get("category") == "authenticity" and row.get("severity") in {"review", "high"}
            for row in analysis.get("signals", [])
        )
    return {"checks": checks, "expected_fields": expected, "recovered_fields": recovered, "passed": all(checks.values())}


def run_case(client: httpx.Client, pack: Path, case: dict, run_suffix: str, timeout_seconds: float) -> dict:
    claim_id = f"CLM-BENCH-{run_suffix}-{case['key'].upper().replace('_', '-')}-{uuid4().hex[:5]}"[:64]
    folder = pack / case["folder"]
    intake = {
        "claim_amount": case["amount"], "incident_date": case["date"], "plate_number": case["plate"],
        "tabular_features": SAMPLE_FEATURES,
        "relationship_entities": {"contact_phone": case["phone"], "repair_shop": case["garage"]},
        "required_evidence": ["claim-intake", "vehicle_image", "claim_document", "relationship-graph"],
    }
    print(f"\n[{case['key']}] tạo {claim_id}", flush=True)
    _request(client, "POST", f"/claims/{claim_id}/intake", json=intake)
    upload(client, claim_id, "image", folder / case["image"])
    upload(client, claim_id, "document", folder / case["document"])
    job = wait_job(
        client, claim_id,
        _request(client, "POST", f"/claims/{claim_id}/analysis-jobs", json={}), timeout_seconds,
    )
    analysis = _request(client, "GET", f"/claims/{claim_id}/analysis")
    evaluation = evaluate_business(case["key"], analysis)
    print(f"  hoàn tất {job['elapsed_seconds']}s · business gate={evaluation['passed']}", flush=True)
    return {
        "case_key": case["key"], "claim_id": claim_id,
        "elapsed_seconds": job["elapsed_seconds"], "cache_hit": job["cache_hit"],
        "stage_durations_seconds": job.get("stage_durations_seconds", {}),
        "analysis_status": analysis.get("analysis_status"),
        "priority": analysis.get("priority"),
        "signal_count": len(analysis.get("signals", [])),
        "module_status": analysis.get("module_status", {}),
        "business_gate": evaluation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pack-root", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/benchmarks/demo_v2_runtime.json")
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--cold-baseline-claim-id")
    parser.add_argument("--cold-baseline-job-id")
    args = parser.parse_args()
    pack = (args.pack_root or find_pack()).resolve()
    run_suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")[-10:]
    started = time.perf_counter()
    with httpx.Client(
        base_url=args.base_url, timeout=60,
        limits=httpx.Limits(max_keepalive_connections=0),
    ) as client:
        health = _request(client, "GET", "/health")
        readiness = _request(client, "GET", "/readiness")
        cold_baseline = None
        if args.cold_baseline_claim_id and args.cold_baseline_job_id:
            cold_baseline = _request(
                client, "GET",
                f"/claims/{args.cold_baseline_claim_id}/analysis-jobs/{args.cold_baseline_job_id}",
            )
        results = [run_case(client, pack, case, run_suffix, args.timeout_seconds) for case in CASES]
        first = results[0]
        print("\n[cache] chạy lại hồ sơ 01 không đổi", flush=True)
        cache_job = wait_job(
            client, first["claim_id"],
            _request(client, "POST", f"/claims/{first['claim_id']}/analysis-jobs", json={}),
            args.timeout_seconds,
        )
    stage_totals: dict[str, float] = {}
    for row in results:
        for stage, seconds in row["stage_durations_seconds"].items():
            stage_totals[stage] = round(stage_totals.get(stage, 0.0) + float(seconds), 1)
    ranked = sorted(stage_totals.items(), key=lambda item: item[1], reverse=True)
    report = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "synthetic_demo_runtime_benchmark_only", "accuracy_claim_allowed": False,
        "pack_root": str(pack), "base_url": args.base_url, "health": health, "readiness": readiness,
        "cases": results,
        "summary": {
            "case_count": len(results), "business_gate_passed": sum(row["business_gate"]["passed"] for row in results),
            "full_run_seconds": round(time.perf_counter() - started, 1),
            "slowest_stages_total": [{"stage": stage, "seconds": seconds} for stage, seconds in ranked],
            "cache_rerun_seconds": cache_job["elapsed_seconds"],
            "cache_hit": cache_job["cache_hit"],
            "cold_baseline": ({
                "claim_id": args.cold_baseline_claim_id,
                "elapsed_seconds": cold_baseline.get("elapsed_seconds"),
                "stage_durations_seconds": cold_baseline.get("stage_durations_seconds", {}),
            } if cold_baseline else None),
        },
        "limitations": [
            "Synthetic cases measure orchestration and latency, not model accuracy.",
            "Cold/warm timing applies only to the current machine and dependency versions.",
            "Business UAT and Vietnamese-domain validation remain required.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nBáo cáo: {args.output.resolve()}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if report["summary"]["business_gate_passed"] != len(CASES) or not cache_job["cache_hit"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
