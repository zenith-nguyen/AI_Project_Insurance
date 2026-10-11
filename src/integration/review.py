"""Combine independently versioned signals into a reviewer-facing result."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .consistency import ConsistencyCheck


@dataclass
class ClaimReviewResult:
    claim_id: str
    damage: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = field(default_factory=list)
    consistency_checks: list[ConsistencyCheck] = field(default_factory=list)
    graph_features: dict[str, Any] = field(default_factory=dict)
    tabular_risk: dict[str, Any] | None = None
    model_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        failed = [check for check in self.consistency_checks if check.status == "fail"]
        unknown = [check for check in self.consistency_checks if check.status == "unknown"]
        return {
            "claim_id": self.claim_id,
            "decision": "human_review",
            "human_review_required": True,
            "summary": {
                "failed_consistency_checks": len(failed),
                "unknown_consistency_checks": len(unknown),
            },
            "damage": self.damage,
            "documents": self.documents,
            "consistency_checks": [asdict(check) for check in self.consistency_checks],
            "graph_features": self.graph_features,
            "tabular_risk": self.tabular_risk,
            "model_versions": self.model_versions,
        }
