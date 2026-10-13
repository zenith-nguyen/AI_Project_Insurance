from scripts.check_live_readiness import check


def test_readiness_reports_core_and_optional_modules():
    report = check()
    assert report["core_live_ready"] is True
    assert set(report["modules"]) == {"tabular_risk", "damage_segmentation", "document_kie"}
    assert report["modules"]["tabular_risk"]["artifact"]["status"] == "ready"
    assert isinstance(report["multimodal_live_ready"], bool)
