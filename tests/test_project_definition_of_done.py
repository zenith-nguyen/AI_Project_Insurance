from scripts.check_project_done import evaluate


def test_engineering_foundation_is_machine_verifiable():
    report = evaluate(level="engineering_foundation")
    assert report["done"] is True
    assert report["automated_ready"] is True
    assert report["blockers"] == []


def test_research_handoff_remains_blocked_until_multimodal_and_human_gates_pass():
    report = evaluate(level="research_handoff")
    assert report["done"] is False
    assert "multimodal_live_not_ready" in report["blockers"]
    assert any(item.startswith("manual_gate:") for item in report["blockers"])
