import json
from pathlib import Path


NOTEBOOK = Path("notebooks/CarDD_YOLOv8s_Candidate_Acc2_v3.ipynb")


def test_acc2_candidate_uses_renamed_active_project_everywhere():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    combined = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )

    expected_active = "/content/drive/MyDrive/AI_Project_Insurance_Acc 2"
    expected_bronze = "/content/drive/MyDrive/AI_Project_Insurance_OLD"
    assert expected_active in combined
    assert expected_bronze in combined
    assert 'MY_DRIVE / "AI_Project_Insurance_Acc 2"' in combined
    assert 'Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")' in combined
    assert 'Path("/content/drive/MyDrive/AI_Project_Insurance")' not in combined
    assert 'MY_DRIVE / "AI_Project_Insurance"' not in combined
    assert 'RUN_FINAL_TEST = False' in combined
    assert 'split="test"' not in combined
    assert '"test": "images/test"' not in combined
    assert "Ã" not in combined
    assert "áº" not in combined

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"acc2_candidate_cell_{index}", "exec")
