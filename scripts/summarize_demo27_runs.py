"""Build an auditable run matrix for the normalized 27-case demo suite."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = args.pack.resolve()
    suite = json.loads((pack / "suite_manifest.json").read_text(encoding="utf-8-sig"))
    receipts: dict[str, list[tuple[float, dict]]] = {}
    for path in (pack / "run_receipts").glob("*.json") if (pack / "run_receipts").is_dir() else []:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        receipts.setdefault(str(payload.get("source_case_id")), []).append((path.stat().st_mtime, payload))
    rows = []
    for case in suite["cases"]:
        expected = json.loads((pack / case["expected_file"]).read_text(encoding="utf-8-sig"))
        runs = receipts.get(case["claim_id"], [])
        receipt = max(runs, default=(0, None), key=lambda item: item[0])[1]
        actual = (receipt or {}).get("actual_summary")
        rows.append({
            "source_case_id": case["claim_id"],
            "scenario": case["scenario"],
            "role": case["role"],
            "expected_route": expected.get("expected_route"),
            "run_status": "analyzed" if actual else ("imported_only" if receipt else "not_run"),
            "runtime_claim_id": (receipt or {}).get("runtime_claim_id"),
            "actual_analysis_status": (actual or {}).get("analysis_status"),
            "actual_priority": (actual or {}).get("priority"),
            "human_signoff": "pending",
        })
    counts = {
        status: sum(row["run_status"] == status for row in rows)
        for status in ("analyzed", "imported_only", "not_run")
    }
    report = {
        "schema_version": "demo27_run_matrix_v1",
        "case_count": len(rows),
        "run_counts": counts,
        "automated_business_pass_claimed": False,
        "meaning": "Expected route and actual output are shown side by side for human UAT sign-off.",
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "case_count": len(rows), **counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
