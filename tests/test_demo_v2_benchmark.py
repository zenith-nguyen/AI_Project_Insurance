from scripts.benchmark_demo_v2 import evaluate_business


def analysis_payload(*, relationship: bool = False, authenticity: bool = False) -> dict:
    modules = {
        name: {"status": "completed"}
        for name in (
            "tabular_risk", "media_authenticity", "damage_segmentation",
            "document_pipeline", "consistency", "relationships",
        )
    }
    return {
        "trace_id": "trace-1", "model_versions": {"tabular_risk": "v1"},
        "evidence": [{"kind": "image"}, {"kind": "document"}],
        "module_status": modules,
        "graph_features": {"related_claim_ids": ["CLM-OLD"] if relationship else []},
        "signals": [{"category": "authenticity", "severity": "review"}] if authenticity else [],
        "extracted_fields": {"document_results": [{"fields": [
            {"field_name": "document_date", "normalized_value": "2026-10-09"},
            {"field_name": "total_amount", "normalized_value": 31_600_000.0},
            {"field_name": "plate_number", "normalized_value": "59H24681"},
        ]}]},
    }


def test_demo_v2_business_gates_are_case_specific():
    assert evaluate_business("hatchback_full", analysis_payload())["passed"] is True
    van = analysis_payload(relationship=True)
    van["extracted_fields"]["document_results"][0]["fields"] = [
        {"field_name": "document_date", "normalized_value": "2026-10-10"},
        {"field_name": "total_amount", "normalized_value": 24_900_000.0},
        {"field_name": "plate_number", "normalized_value": "50D61537"},
    ]
    assert evaluate_business("van_relationship", van)["passed"] is True
    sedan = analysis_payload(authenticity=True)
    sedan["extracted_fields"]["document_results"][0]["fields"] = [
        {"field_name": "document_date", "normalized_value": "2026-10-11"},
        {"field_name": "total_amount", "normalized_value": 36_750_000.0},
        {"field_name": "plate_number", "normalized_value": "61A90426"},
    ]
    assert evaluate_business("sedan_authenticity", sedan)["passed"] is True


def test_demo_v2_gate_fails_when_critical_document_field_is_missing():
    payload = analysis_payload()
    payload["extracted_fields"]["document_results"][0]["fields"] = []
    result = evaluate_business("hatchback_full", payload)
    assert result["passed"] is False
    assert result["checks"]["critical_document_fields_recovered"] is False
