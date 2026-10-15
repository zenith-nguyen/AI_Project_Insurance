"""Audit and normalize the external 27-case synthetic demo suite."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.demo_suite import prepare_demo_suite


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = prepare_demo_suite(args.source, args.output, overwrite=args.overwrite)
    audit = result["source_audit"]
    print(json.dumps({
        "output": result["output"],
        "cases": result["case_count"],
        "ocr_pages": result["ocr_benchmark"]["page_count"],
        "integrity_files": result["integrity_file_count"],
        "source_fatal_issues": audit["fatal_issue_count"],
        "source_repairable_issues": audit["repairable_issue_count"],
        "domain_accuracy_claim_allowed": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
