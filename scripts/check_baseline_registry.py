"""Validate baseline ownership, split comparability and reported deltas."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.baselines.registry import load_baseline_registry
from src.registry import load_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    baselines = load_baseline_registry(ROOT / "configs/baseline_registry.v1.yaml")
    models = load_registry(ROOT / "configs/model_registry.v1.yaml")
    checks: list[dict] = []
    checks.append({
        "name": "module_coverage",
        "passed": set(baselines.modules) == set(models.modules),
        "detail": f"baseline={len(baselines.modules)}, model={len(models.modules)}",
    })
    for name, module in baselines.modules.items():
        comparison = module["comparison"]
        if comparison["comparable"]:
            same_split = module["baseline"]["split"] == module["current"]["split"]
            observed = float(module["current"]["value"]) - float(module["baseline"]["value"])
            delta_matches = abs(observed - float(comparison["delta"])) < 1e-9
            direction_ok = (
                comparison["direction"] == "higher_is_better" and observed > 0
            ) or (
                comparison["direction"] == "lower_is_better" and observed < 0
            )
            checks.extend([
                {"name": f"{name}.same_split", "passed": same_split, "detail": module["baseline"]["split"]},
                {"name": f"{name}.delta", "passed": delta_matches, "detail": observed},
                {"name": f"{name}.direction", "passed": direction_ok, "detail": comparison["direction"]},
            ])
        else:
            checks.append({
                "name": f"{name}.no_false_uplift",
                "passed": comparison["delta"] is None,
                "detail": comparison["conclusion"],
            })
    payload = {
        "schema_version": "baseline_registry_check_v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "checks": checks,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        target = args.output if args.output.is_absolute() else ROOT / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
