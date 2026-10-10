import json
from pathlib import Path


NOTEBOOK = Path("notebooks/CarDD_Final_Test_Report_Reader_Acc2_v1.ipynb")


def test_report_reader_is_read_only_and_checks_execution_artifacts():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    combined = "\n".join(code_cells)

    assert "AI_Project_Insurance_Acc 2" in combined
    assert "cardd_yolov8s_seg_final_test_v1.json" in combined
    assert "cardd_yolov8s_seg_final_test_v1.execution.json" in combined
    assert "EXPECTED_TEST_IMAGES = 419" in combined
    assert "EXPECTED_TEST_INSTANCES = 931" in combined
    assert "6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b" in combined
    assert 'execution.get("status") == "completed"' in combined
    assert "same_run_id" in combined
    assert "lock_report_hash" in combined
    assert ".val(" not in combined
    assert "from ultralytics" not in combined
    assert "RUN_FINAL_TEST" not in combined

    for index, source in enumerate(code_cells):
        compile(source, f"report_reader_cell_{index}", "exec")
