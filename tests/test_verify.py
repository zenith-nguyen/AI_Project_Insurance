from src.api.schemas import ClaimAnalysis, Signal
from src.api.verify import route_analysis
from src.api.operations_log import VerificationLog
from fastapi.testclient import TestClient
from src.api.app import app


def make_analysis(**changes):
    values = dict(claim_id="C-1", trace_id="t", created_at="2026-10-24T00:00:00Z",
                  mode="live", priority="normal", research_risk_score=0.1,
                  evidence_completeness=1.0)
    values.update(changes)
    return ClaimAnalysis(**values)


def test_routing_never_treats_missing_or_blocked_as_low_risk():
    for changes in ({"research_risk_score": None}, {"analysis_status": "partial"},
                    {"missing_evidence": ["photo"]}, {"evidence_completeness": 0.5}):
        response = route_analysis(make_analysis(**changes))
        assert response.action == "SUPPLEMENT"
        assert response.human_review_required
        assert not response.risk_score_is_probability


def test_high_risk_routes_to_siu_and_normal_is_only_a_suggestion():
    high = route_analysis(make_analysis(priority="high", research_risk_score=0.8))
    assert high.action == "SIU"
    normal = route_analysis(make_analysis())
    assert normal.action == "STP"
    assert normal.human_review_required


def test_live_tabular_threshold_signal_maps_to_queue_action():
    high = Signal(signal_id="tabular-priority", category="risk", title="Risk queue",
                  explanation="threshold", severity="high", evidence_ids=["claim-intake"])
    review = high.model_copy(update={"severity": "review"})
    siu = route_analysis(make_analysis(signals=[high]))
    supplement = route_analysis(make_analysis(signals=[review]))
    assert siu.action == "SIU" and "t2" in siu.reasons[0]
    assert supplement.action == "SUPPLEMENT" and "t1" in supplement.reasons[0]
    assert siu.evidence_refs == ["claim-intake"]


def test_verify_api_retains_human_gate_and_demo_disclosure():
    result = TestClient(app).post("/verify", json={"claim_id": "CLM-VERIFY-DEMO"})
    assert result.status_code == 200
    body = result.json()
    assert body["claim_id"] == "CLM-VERIFY-DEMO"
    assert body["human_review_required"] is True
    assert body["risk_score_is_probability"] is False
    assert body["mode"] == "fixture"
    assert any("fixture" in reason for reason in body["reasons"])
    assert result.headers["x-trace-id"]


def test_verification_log_has_routing_telemetry_without_raw_inputs(tmp_path):
    import json

    path = tmp_path / "verify.jsonl"
    response = route_analysis(make_analysis(priority="high"))
    VerificationLog(path).append(response, 25.25)
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["claim_id"] == "C-1"
    assert row["action"] == "SIU"
    assert row["duration_ms"] == 25.2
    assert "research_risk_score" not in row
    assert "evidence" not in row
