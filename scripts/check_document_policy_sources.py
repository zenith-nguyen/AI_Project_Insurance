"""Check reachability/change hints for official VN document-policy sources.

This command is deliberately read-only.  It produces evidence for a human
policy review and never modifies document acceptance rules automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document.policy import DocumentPolicyRegistry


def probe(url: str, timeout: float = 20.0) -> dict:
    request = Request(url, headers={"User-Agent": "InsuranceDocumentPolicyMonitor/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URLs come from reviewed config
            body = response.read(2 * 1024 * 1024)
            return {
                "reachable": 200 <= response.status < 400,
                "http_status": response.status,
                "final_url": response.geturl(),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "sample_sha256": hashlib.sha256(body).hexdigest(),
                "sample_bytes": len(body),
                "error": None,
            }
    except Exception as error:
        return {
            "reachable": False, "http_status": None, "final_url": url,
            "etag": None, "last_modified": None, "sample_sha256": None,
            "sample_bytes": 0, "error": f"{type(error).__name__}: {error}",
        }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/vietnam_document_policy.v1.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/governance/document_policy_source_check.json")
    args = parser.parse_args()
    registry = DocumentPolicyRegistry.load(args.config).public_summary()
    sources = {
        source_id: {**source, **probe(source["url"])}
        for source_id, source in registry["official_sources"].items()
    }
    report = {
        "schema_version": "document_policy_source_check_v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": registry["jurisdiction"],
        "registry_schema_version": registry["schema_version"],
        "all_sources_reachable": all(row["reachable"] for row in sources.values()),
        "sources": sources,
        "decision": "human_policy_review_required",
        "meaning": "Reachability or page hash changes are monitoring signals only; they do not update claim rules automatically.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
