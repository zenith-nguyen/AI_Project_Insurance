"""Versioned model-registry reader used by the API and release checks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RegisteredModel:
    name: str
    implementation: str
    version: str
    task: str
    artifact_uri: str
    artifact_hash: str
    evidence: str
    primary_metric: str
    metric_value: float
    evaluation_split: str
    status: str


@dataclass(frozen=True)
class ModelRegistry:
    schema_version: str
    product_version: str
    generated_at: str
    modules: dict[str, RegisteredModel]

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product_version": self.product_version,
            "models": {
                name: {
                    "implementation": model.implementation,
                    "version": model.version,
                    "task": model.task,
                    "status": model.status,
                    "primary_metric": model.primary_metric,
                    "metric_value": model.metric_value,
                }
                for name, model in self.modules.items()
            },
        }


def load_registry(path: str | Path) -> ModelRegistry:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    required = {"schema_version", "product_version", "generated_at", "modules"}
    missing = required.difference(payload or {})
    if missing:
        raise ValueError(f"Model registry is missing: {sorted(missing)}")
    modules: dict[str, RegisteredModel] = {}
    for name, values in payload["modules"].items():
        modules[name] = RegisteredModel(name=name, **values)
    if not modules:
        raise ValueError("Model registry must contain at least one module.")
    return ModelRegistry(
        schema_version=str(payload["schema_version"]),
        product_version=str(payload["product_version"]),
        generated_at=str(payload["generated_at"]),
        modules=modules,
    )
