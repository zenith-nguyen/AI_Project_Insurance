"""Import one normalized demo27 case into the live API, optionally seed its scoped history."""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def _upload(client: httpx.Client, claim_id: str, kind: str, path: Path) -> dict:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as stream:
        return _request(
            client, "POST", f"/claims/{claim_id}/evidence", data={"kind": kind},
            files={"file": (path.name, stream, content_type)},
        )


def _runtime_id(source_id: str, suffix: str) -> str:
    value = f"D27-{source_id}-{suffix}".upper().replace("_", "-")
    return value[:64]


def _relationship_entities(row: dict, relationship_scope: str | None = None) -> dict[str, str]:
    values = {}
    for source, target in (("vehicle_id", "vehicle_id"), ("contact_id", "contact_id"), ("garage_id", "repair_shop")):
        if row.get(source):
            values[target] = str(row[source])
    if relationship_scope:
        values["relationship_scope"] = relationship_scope
    return values


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _point_in_time_history(rows: list[dict], target_claim_id: str, target_scored_at: str) -> list[dict]:
    """Keep demo references historical without changing their relative spacing.

    The supplied SC07 fixture places reference claims after the target even though
    its expected result assumes those links are already visible. Production graph
    code must never look into the future, so synthetic UAT mirrors future offsets
    backwards and records both timestamps in the import receipt.
    """
    target_time = _parse_timestamp(target_scored_at)
    prepared: list[dict] = []
    same_time_index = 0
    for row in rows:
        if row.get("claim_id") == target_claim_id:
            continue
        original = str(row["submitted_at"])
        observed = _parse_timestamp(original)
        rebased = False
        if observed >= target_time:
            delta = observed - target_time
            if delta <= timedelta(0):
                same_time_index += 1
                delta = timedelta(seconds=same_time_index)
            observed = target_time - delta
            rebased = True
        prepared.append({
            **row,
            "original_submitted_at": original,
            "submitted_at": observed.isoformat(),
            "timestamp_rebased_for_point_in_time_uat": rebased,
        })
    return prepared


def _seed_history(client: httpx.Client, pack: Path, source_claim: dict, suffix: str) -> list[dict]:
    seeded: list[dict] = []
    case_folder = pack / "cases" / source_claim["claim_id"]
    related_path = case_folder / "related_claims.json"
    reference_path = case_folder / "reference_claims.json"
    if related_path.is_file():
        rows = _point_in_time_history(
            json.loads(related_path.read_text(encoding="utf-8-sig")),
            source_claim["claim_id"], source_claim["submitted_at"],
        )
        for row in rows:
            claim_id = _runtime_id(str(row["claim_id"]), suffix)
            _request(client, "POST", f"/claims/{claim_id}/intake", json={
                "scored_at": row.get("submitted_at"),
                "plate_number": source_claim.get("vehicle", {}).get("plate_declared"),
                "relationship_entities": _relationship_entities(row, f"demo27-{suffix}"),
                "required_evidence": ["claim-intake"],
            })
            seeded.append({
                "runtime_claim_id": claim_id,
                "source_claim_id": row["claim_id"],
                "original_scored_at": row["original_submitted_at"],
                "imported_scored_at": row["submitted_at"],
                "timestamp_rebased_for_point_in_time_uat": row["timestamp_rebased_for_point_in_time_uat"],
            })
    if reference_path.is_file():
        rows = json.loads(reference_path.read_text(encoding="utf-8-sig"))
        for row in rows:
            claim_id = _runtime_id(str(row["claim_id"]), suffix)
            _request(client, "POST", f"/claims/{claim_id}/intake", json={
                "scored_at": row.get("submitted_at"), "plate_number": row.get("plate"),
                "relationship_entities": {"relationship_scope": f"demo27-{suffix}"},
                "required_evidence": ["claim-intake", "vehicle_image"],
            })
            for relative in row.get("image_files", []):
                source = pack / "assets" / "vehicle_images" / Path(relative).name
                _upload(client, claim_id, "image", source)
            seeded.append({
                "runtime_claim_id": claim_id,
                "source_claim_id": row["claim_id"],
                "original_scored_at": row.get("submitted_at"),
                "imported_scored_at": row.get("submitted_at"),
                "timestamp_rebased_for_point_in_time_uat": False,
            })
    return seeded


def _wait(client: httpx.Client, claim_id: str, job: dict, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_stage = None
    while job["status"] in {"queued", "running"}:
        if job["stage"] != last_stage:
            print(f"{job['stage']}: {job['message']}", flush=True)
            last_stage = job["stage"]
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Analysis exceeded {timeout:.0f} seconds")
        time.sleep(1)
        job = _request(client, "GET", f"/claims/{claim_id}/analysis-jobs/{job['job_id']}")
    if job["status"] != "completed":
        raise RuntimeError(job.get("error") or "Analysis failed")
    return job


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--case", required=True, help="Source case ID, for example CLM-07-P")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runtime-claim-id")
    parser.add_argument("--documents", choices=("none", "minimal", "full"), default="minimal")
    parser.add_argument("--seed-history", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    pack = args.pack.resolve()
    suite = json.loads((pack / "suite_manifest.json").read_text(encoding="utf-8-sig"))
    case = next((row for row in suite["cases"] if row["claim_id"] == args.case), None)
    if case is None:
        raise KeyError(f"Unknown demo27 case: {args.case}")
    source_claim = json.loads((pack / case["claim_file"]).read_text(encoding="utf-8-sig"))
    suffix = datetime.now().strftime("%m%d%H%M%S")
    claim_id = args.runtime_claim_id or _runtime_id(args.case, suffix)
    expected = json.loads((pack / case["expected_file"]).read_text(encoding="utf-8-sig"))
    relationship_entities = {}
    related_path = pack / "cases" / args.case / "related_claims.json"
    if related_path.is_file():
        related = json.loads(related_path.read_text(encoding="utf-8-sig"))
        current = next((row for row in related if row.get("claim_id") == args.case), {})
        relationship_entities = _relationship_entities(current, f"demo27-{suffix}")

    with httpx.Client(base_url=args.base_url, timeout=90, limits=httpx.Limits(max_keepalive_connections=0)) as client:
        seeded = _seed_history(client, pack, source_claim, suffix) if args.seed_history else []
        intake = {
            "claim_amount": source_claim.get("claim_amount_vnd"),
            "incident_date": str(source_claim.get("incident_at", ""))[:10] or None,
            "plate_number": source_claim.get("vehicle", {}).get("plate_declared"),
            "scored_at": source_claim.get("submitted_at"),
            "relationship_entities": relationship_entities,
            "required_evidence": ["claim-intake", "vehicle_image", "claim_document"],
        }
        _request(client, "POST", f"/claims/{claim_id}/intake", json=intake)
        uploaded = []
        for relative in case["vehicle_images"]:
            uploaded.append(_upload(client, claim_id, "image", pack / relative))
        if args.documents != "none":
            document_key = "minimal_documents" if args.documents == "minimal" else "full_documents"
            for relative in case[document_key]:
                uploaded.append(_upload(client, claim_id, "document", pack / relative))
        job = analysis = None
        if args.analyze:
            job = _wait(
                client, claim_id,
                _request(client, "POST", f"/claims/{claim_id}/analysis-jobs", json={}),
                args.timeout_seconds,
            )
            analysis = _request(client, "GET", f"/claims/{claim_id}/analysis")

    receipt = {
        "schema_version": "demo27_import_receipt_v1",
        "source_case_id": args.case,
        "runtime_claim_id": claim_id,
        "expected_route": expected.get("expected_route"),
        "expected_signal": expected.get("expected_signal"),
        "seeded_history": seeded,
        "seeded_history_claim_ids": [row["runtime_claim_id"] for row in seeded],
        "uploaded_evidence": [{key: row.get(key) for key in ("evidence_id", "kind", "original_filename", "sha256")} for row in uploaded],
        "analysis_job": job,
        "actual_summary": None if analysis is None else {
            "analysis_status": analysis.get("analysis_status"),
            "priority": analysis.get("priority"),
            "signal_titles": [row.get("title") for row in analysis.get("signals", [])],
            "related_claim_ids": analysis.get("graph_features", {}).get("related_claim_ids", []),
        },
        "limitations": [
            "Synthetic demo case; expected route is a workflow oracle, not a fraud label.",
            "XGBoost remains unscored because the pack does not contain its full tabular feature schema.",
        ],
    }
    receipt_path = args.receipt or pack / "run_receipts" / f"{claim_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "runtime_claim_id": claim_id, "uploaded": len(uploaded), "seeded_history": len(seeded),
        "analyzed": analysis is not None, "receipt": str(receipt_path),
        "workbench": f"{args.base_url}/?claim_id={claim_id}",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
