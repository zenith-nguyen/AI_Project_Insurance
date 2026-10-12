from __future__ import annotations

import ast
import json
from pathlib import Path


NOTEBOOK = Path("notebooks/Document_DiT_Independent_Validation_Acc2_v2.ipynb")


def _notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def test_dit_v2_uses_pinned_parquet_mirror_without_loader_script() -> None:
    notebook = _notebook()
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    code_source = "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )

    assert 'MIRROR_ID = "chainyo/rvl-cdip"' in source
    assert 'MIRROR_REVISION = "66f430a1252ea1732413a80a56a1b6e8bc74264e"' in source
    assert 'SOURCE_SPLIT = "val"' in source
    assert "trust_remote_code" not in code_source
    assert "rvl_cdip.py" in source  # explanatory markdown only
    assert 'RUN_FINAL_TEST = False' in source
    assert '"test_used": False' in source


def test_dit_v2_persists_resumable_balanced_sample() -> None:
    source = "\n".join("".join(cell["source"]) for cell in _notebook()["cells"])

    assert "sample_manifest.jsonl" in source
    assert "SAMPLES_PER_CLASS = 20" in source
    assert "EXPECTED_CLASSES = 16" in source
    assert "sha256" in source
    assert "handle.flush()" in source


def test_dit_v2_code_cells_compile() -> None:
    for index, cell in enumerate(_notebook()["cells"]):
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), filename=f"cell-{index}")
