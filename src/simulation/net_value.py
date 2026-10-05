"""Net value framework; requires supplied business inputs before calculation."""
from __future__ import annotations

from src.data.common import config


REQUIRED = ("fraud_loss_avoided", "review_cost", "siu_cost", "false_hold_cost", "ai_operation_cost_per_claim")


def net_value(*, caught_fraud: int, reviewed: int, siu: int, false_holds: int, total_claims: int, assumptions: dict | None = None) -> float:
    inputs = assumptions if assumptions is not None else config("configs/business.yaml")
    missing = [key for key in REQUIRED if inputs.get(key) is None]
    if missing:
        raise ValueError(f"Business assumptions required before Net Value: {', '.join(missing)}")
    if any(inputs[key] < 0 for key in REQUIRED):
        raise ValueError("Costs and prevented loss must be nonnegative")
    return (caught_fraud * inputs["fraud_loss_avoided"] - reviewed * inputs["review_cost"] - siu * inputs["siu_cost"] - false_holds * inputs["false_hold_cost"] - total_claims * inputs["ai_operation_cost_per_claim"])
