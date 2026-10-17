"""Versioned baseline registry with explicit ownership and comparability rules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


VALID_ORIGINS = {
    "team_implemented",
    "team_trained_from_external_weights",
    "external_pretrained_team_evaluated",
    "deterministic_engineering",
}


@dataclass(frozen=True)
class BaselineRegistry:
    schema_version: str
    updated_at: str
    definitions: dict[str, str]
    modules: dict[str, dict[str, Any]]

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "updated_at": self.updated_at,
            "definitions": self.definitions,
            "modules": self.modules,
        }


def load_baseline_registry(path: str | Path) -> BaselineRegistry:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    required = {"schema_version", "updated_at", "definitions", "modules"}
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Baseline registry is missing: {sorted(missing)}")
    if not payload["modules"]:
        raise ValueError("Baseline registry must contain at least one module.")
    for module_name, module in payload["modules"].items():
        for key in ("baseline", "current", "comparison", "business_meaning", "decision", "limitation"):
            if key not in module:
                raise ValueError(f"Baseline module {module_name!r} is missing {key!r}.")
        for stage in ("baseline", "current"):
            origin = module[stage].get("origin_type")
            if origin not in VALID_ORIGINS:
                raise ValueError(f"Invalid origin_type {origin!r} for {module_name}.{stage}.")
        comparison = module["comparison"]
        if comparison.get("comparable") and comparison.get("delta") is None:
            raise ValueError(f"Comparable module {module_name!r} requires a delta.")
        if not comparison.get("comparable") and comparison.get("delta") is not None:
            raise ValueError(f"Non-comparable module {module_name!r} must not publish a delta.")
    return BaselineRegistry(
        schema_version=str(payload["schema_version"]),
        updated_at=str(payload["updated_at"]),
        definitions={str(key): str(value) for key, value in payload["definitions"].items()},
        modules=payload["modules"],
    )
