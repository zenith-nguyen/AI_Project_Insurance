import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/Document_LayoutLMv3_Final_Test_Acc2_v3.ipynb"


def notebook_source() -> str:
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])


def test_final_test_notebook_is_checkpoint_locked_and_evaluation_only():
    source = notebook_source()
    assert "RUN_FINAL_TEST = True" in source
    assert "EXPECTED_TEST_ROWS = 361" in source
    assert ".shortcut-targets-by-id" in source
    assert "matching_projects" in source
    assert 'DATA_ROOT/"test.parquet"' in source
    assert 'selection.get("candidate_selected")' in source
    assert 'selection["checkpoint_tree_sha256"]' in source
    assert "if FINAL_REPORT.exists()" in source
    assert "if EXECUTION_LOCK.exists()" in source
    assert '"test_run_number":1' in source
    assert '"test_used_for_selection":False' in source
    assert "trainer.evaluate()" in source
    assert "trainer.train()" not in source
    assert "final_report_sha256" in source


def test_every_code_cell_compiles_before_colab_upload():
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for index, cell in enumerate(payload["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell.get("source", [])), f"cell-{index}", "exec")
