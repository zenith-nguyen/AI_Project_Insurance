"""Check local artifacts, hashes and optional runtime dependencies.

The normal command succeeds when the core tabular live slice is ready. Pass
--require-all when preparing the multimodal integration machine.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hash_artifact import file_hash, tree_hash
from src.registry import load_registry



def _dependencies(names: tuple[str, ...]) -> dict:
    missing = [name for name in names if importlib.util.find_spec(name) is None]
    return {"ready": not missing, "missing": missing}


def _artifact(path: Path, expected: str) -> dict:
    if not path.exists():
        return {"ready": False, "status": "missing", "path": str(path), "actual_hash": None}
    actual = tree_hash(path) if path.is_dir() else file_hash(path)
    return {
        "ready": actual.casefold() == expected.casefold(),
        "status": "ready" if actual.casefold() == expected.casefold() else "hash_mismatch",
        "path": str(path), "actual_hash": actual,
    }


def check(root: Path = ROOT) -> dict:
    registry = load_registry(root / "configs/model_registry.v1.yaml")
    paths = {
        "tabular_risk": root / "artifacts/models/tabular_v1/bundle.joblib",
        "damage_segmentation": root / "artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt",
        "document_kie": root / "artifacts/models/document_kie/layoutlmv3_sroie_candidate_v2/checkpoint-264",
    }
    modules = {
        name: {"artifact": _artifact(path, registry.modules[name].artifact_hash)}
        for name, path in paths.items()
    }
    modules["tabular_risk"]["dependencies"] = _dependencies(("joblib", "pandas", "numpy", "sklearn"))
    modules["damage_segmentation"]["dependencies"] = _dependencies(("ultralytics",))
    modules["document_kie"]["dependencies"] = _dependencies(("torch", "transformers", "paddle", "paddleocr", "pypdfium2"))
    for payload in modules.values():
        payload["ready"] = payload["artifact"]["ready"] and payload["dependencies"]["ready"]
    return {
        "core_live_ready": modules["tabular_risk"]["ready"],
        "multimodal_live_ready": all(item["ready"] for item in modules.values()),
        "modules": modules,
        "next_action": (
            "Run scripts/run_live.ps1."
            if all(item["ready"] for item in modules.values())
            else "Copy missing registered checkpoints with scripts/setup_live.ps1 -ArtifactRoot <path>, then install the listed dependencies."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    report = check()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    ready = report["multimodal_live_ready"] if args.require_all else report["core_live_ready"]
    if not ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
