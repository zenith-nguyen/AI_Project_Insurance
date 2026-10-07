import json
from pathlib import Path


NOTEBOOK = Path("notebooks/CarDD_YOLOv8s_Candidate_Pro_Account_v2.ipynb")


def test_pro_account_candidate_is_self_contained_compilable_and_test_locked():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    combined = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )

    assert "hoanganhthu01230@gmail.com" in combined
    assert 'MY_DRIVE / "AI_Project_Insurance"' in combined
    assert 'MY_DRIVE / "AI_Project_Insurance_OLD"' in combined
    assert 'probe.write_text("write-access-ok"' in combined
    assert 'YOLO("yolov8s-seg.pt").train' in combined
    assert 'RUN_FINAL_TEST = False' in combined
    assert 'split="test"' not in combined
    assert '"test": "images/test"' not in combined
    assert "Ã" not in combined
    assert "áº" not in combined

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"pro_candidate_cell_{index}", "exec")
