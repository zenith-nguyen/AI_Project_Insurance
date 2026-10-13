"""Evaluate the versioned Definition of Done without turning missing evidence into PASS."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_live_readiness import check as check_live


def evaluate(root: Path = ROOT, level: str | None = None) -> dict:
    config_path = root / "configs/project_definition_of_done_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    selected = level or config["target_release"]
    if selected not in config["levels"]:
        raise ValueError(f"Unknown Definition of Done level: {selected}")

    level_config = config["levels"][selected]
    files = {relative: (root / relative).is_file() for relative in config["required_files"]}
    contract_path = root / "contracts/claim_review_openapi.v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.is_file() else {"paths": {}}
    endpoints = {endpoint: endpoint in contract.get("paths", {}) for endpoint in config["required_endpoints"]}
    live = check_live(root)
    required_manual = level_config.get("required_manual_gates", [])
    manual = {name: bool(config["manual_gates"].get(name, False)) for name in required_manual}
    automated_ready = all(files.values()) and all(endpoints.values()) and live["core_live_ready"]
    if level_config.get("require_multimodal_live"):
        automated_ready = automated_ready and live["multimodal_live_ready"]
    manual_ready = all(manual.values())
    done = automated_ready and manual_ready
    blockers = [f"missing_file:{name}" for name, passed in files.items() if not passed]
    blockers += [f"missing_endpoint:{name}" for name, passed in endpoints.items() if not passed]
    if not live["core_live_ready"]:
        blockers.append("core_live_not_ready")
    if level_config.get("require_multimodal_live") and not live["multimodal_live_ready"]:
        blockers.append("multimodal_live_not_ready")
    blockers += [f"manual_gate:{name}" for name, passed in manual.items() if not passed]
    return {
        "schema_version": config["schema_version"],
        "project": config["project"],
        "level": selected,
        "description": level_config["description"],
        "done": done,
        "automated_ready": automated_ready,
        "manual_ready": manual_ready,
        "checks": {"files": files, "endpoints": endpoints, "live_readiness": live, "manual_gates": manual},
        "blockers": blockers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=("engineering_foundation", "research_handoff", "pilot_ready"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-fail", action="store_true", help="Print status without returning a failing exit code.")
    args = parser.parse_args()
    report = evaluate(level=args.level)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if not report["done"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

