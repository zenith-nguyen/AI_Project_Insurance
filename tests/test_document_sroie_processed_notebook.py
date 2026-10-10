import json
from pathlib import Path


NOTEBOOK = Path("notebooks/Document_SROIE_Processed_Split_Acc2_v1.ipynb")


def test_sroie_processed_split_protocol_is_locked():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    combined = "\n".join(code_cells)

    assert '"source_train": 626' in combined
    assert '"removed": 8' in combined
    assert '"train": 525' in combined
    assert '"validation": 93' in combined
    assert '"test": 361' in combined
    assert "preserve_source_test_and_remove_exact_duplicates_from_train" in combined
    assert '"test_used_for_split_or_selection": False' in combined
    assert "cross_split_exact_duplicates" in combined
    assert "deterministic_group_by_image_sha256_subset_sum" in combined
    assert "image_groups" in combined
    assert "data/processed/documents/sroie/v1" in combined

    for index, source in enumerate(code_cells):
        compile(source, f"sroie_processed_cell_{index}", "exec")
