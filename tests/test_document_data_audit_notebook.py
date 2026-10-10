import json
from pathlib import Path


NOTEBOOK = Path("notebooks/Document_Data_Audit_Acc2_v1.ipynb")


def notebook_code():
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = [
        "".join(cell["source"])
        for cell in payload["cells"]
        if cell["cell_type"] == "code"
    ]
    return cells, "\n".join(cells)


def test_document_audit_is_read_only_and_has_split_leakage_checks():
    cells, combined = notebook_code()

    assert "document_sources_registry.json" in combined
    assert "cross_split_exact_duplicates" in combined
    assert "parquet_image_audit" in combined
    assert "archive.extract" not in combined
    assert "shutil.rmtree" not in combined
    assert "commercial_production_gate" in combined
    assert "PII review is required" in combined
    assert "RVL-CDIP sample: PASS" in combined

    for index, source in enumerate(cells):
        compile(source, f"document_audit_cell_{index}", "exec")


def test_document_audit_expected_counts_are_locked():
    _, combined = notebook_code()

    assert '"train": 800' in combined
    assert '"validation": 100' in combined
    assert '"train": 626' in combined
    assert '"test": 347' in combined
    assert '"sample_rows": 1600' in combined
    assert '"per_class": 100' in combined
