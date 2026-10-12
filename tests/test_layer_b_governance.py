from __future__ import annotations

import csv
from pathlib import Path


def rows() -> list[dict[str, str]]:
    with Path("configs/layer_b_field_governance_v1.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def test_layer_b_governance_covers_39_unique_source_fields() -> None:
    values = rows()
    assert len(values) == 39
    assert len({row["field"] for row in values}) == 39


def test_target_is_post_investigation_and_never_a_feature() -> None:
    target = next(row for row in rows() if row["field"] == "fraud_reported")
    assert target["available_stage"] == "Sau điều tra"
    assert target["reliability_level"] == "Thấp"
    assert target["feature_policy"] == "Target only; cấm làm feature"


def test_known_missing_rates_match_data_audit() -> None:
    rates = {row["field"]: float(row["missing_rate_percent"]) for row in rows()}
    assert rates["collision_type"] == 17.8
    assert rates["authorities_contacted"] == 9.1
    assert rates["property_damage"] == 36.0
    assert rates["police_report_available"] == 34.3

