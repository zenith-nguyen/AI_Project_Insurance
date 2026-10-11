from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def test_current_reports_do_not_repeat_superseded_statuses():
    intake = read("scripts/build_document_data_intake_notebook.py")
    selection = read("reports/handoff/model_selection_matrix.md")
    roadmap = read("reports/SYSTEM_PRODUCTIZATION_ROADMAP_V1.md")
    risk = read("reports/handoff/risk_register_v2_additions.md")

    assert '"expected_test_examples": 361' in intake
    assert '"expected_test_examples": 347' not in intake
    assert "final test đã chạy đúng một lần" in selection
    assert "SROIE đang chờ archive" not in roadmap
    assert "Document source chưa audit" not in risk


def test_progress_pack_sources_cover_required_reports():
    required = [
        "reports/CARDD_BASELINE_V2_RESULTS.md",
        "reports/CARDD_FINAL_TEST_V1.md",
        "reports/DOCUMENT_DATA_AUDIT_RUN_2026-10-11.md",
        "reports/DOCUMENT_EDA_SOURCE_ANALYSIS_V1.md",
        "reports/GROUND_TRUTH_DEFINITION_V1.md",
        "reports/DATA_LEAKAGE_CHECK_V1.md",
        "reports/PRODUCT_MODEL_AND_USAGE_V1.md",
        "reports/CARDD_PICLAB_CONSENT_ACTION_V1.md",
    ]
    assert all(Path(path).is_file() for path in required)
