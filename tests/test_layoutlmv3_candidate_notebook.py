from __future__ import annotations

import ast
import json
from pathlib import Path


NOTEBOOK = Path("notebooks/Document_LayoutLMv3_Candidate_Acc2_v3.ipynb")


def _source() -> str:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


def test_candidate_v3_keeps_test_locked_and_scope_comparable() -> None:
    source = _source()

    assert 'RUN_FINAL_TEST = False' in source
    assert 'FIELD_MAP = {"date":"DATE","total":"TOTAL"}' in source
    assert "MIN_WEAK_ALIGNMENT_COVERAGE = 0.85" in source
    assert "MIN_FIELD_F1_GAIN = 0.02" in source
    assert 'DATA_ROOT/"test.parquet"' not in source


def test_candidate_v3_contains_field_aware_alignment_and_diagnostics() -> None:
    source = _source()

    assert "def parsed_dates(value):" in source
    assert "def parsed_amounts(value):" in source
    assert "Alignment counts:" in source
    assert "Unmatched diagnostics" in source


def test_candidate_v3_code_cells_compile() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), filename=f"cell-{index}")

