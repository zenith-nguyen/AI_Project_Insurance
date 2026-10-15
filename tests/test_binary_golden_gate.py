from scripts.run_binary_golden_claim import STRICT_MODULES, evaluate_gate


def test_binary_golden_gate_rejects_precomputed_or_missing_model_results():
    analysis = {
        "trace_id": "trace-1", "model_versions": {"tabular_risk": "v1"},
        "evidence": [{"kind": "image"}, {"kind": "document"}],
        "module_status": {name: {"status": "completed"} for name in STRICT_MODULES},
    }
    events = [{"event_type": "review"}, {"event_type": "field_correction"}]
    assert evaluate_gate(analysis, events)["passed"] is True

    analysis["module_status"]["document_pipeline"]["status"] = "completed_precomputed"
    result = evaluate_gate(analysis, events)
    assert result["passed"] is False
    assert result["module_pass"]["document_pipeline"] is False
