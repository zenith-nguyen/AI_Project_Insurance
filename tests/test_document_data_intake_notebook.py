import json
from pathlib import Path


NOTEBOOK = Path("notebooks/Document_Data_Intake_Acc2_v1.ipynb")


def notebook_code():
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = [
        "".join(cell["source"])
        for cell in payload["cells"]
        if cell["cell_type"] == "code"
    ]
    return cells, "\n".join(cells)


def test_document_intake_has_governance_and_large_download_gates():
    cells, combined = notebook_code()

    assert "AI_Project_Insurance_Acc 2" in combined
    assert 'BRONZE_ROOT = NEW_PROJECT / "data/bronze/documents"' in combined
    assert "ALLOW_LARGE_DOWNLOADS = False" in combined
    assert "DOWNLOAD_MIDV500_ALL = False" in combined
    assert "DOWNLOAD_RVL_CDIP_FULL = False" in combined
    assert "SROIE_KAGGLE_HANDLE" in combined
    assert '"/versions/" not in SROIE_KAGGLE_HANDLE' in combined
    assert "jsdnrs/ICDAR2019-SROIE" in combined
    assert "bffe40c26759f3376ec2b3ae9031dbba54cd587c" in combined
    assert "expected_train_examples" in combined
    assert "safe_extract_zip" in combined
    assert "Unsafe ZIP member" in combined
    assert "document_sources_registry.json" in combined
    assert "source_manifest.json" in combined
    assert "KAGGLE_KEY" not in combined
    assert "KAGGLE_API_TOKEN=" not in combined
    assert "HF_TOKEN=" not in combined
    assert "shutil.rmtree" not in combined

    for index, source in enumerate(cells):
        compile(source, f"document_intake_cell_{index}", "exec")


def test_document_intake_pins_reproducible_sources_and_keeps_public_data_separate():
    _, combined = notebook_code()

    assert "41b075798d0d9da590a950dac1e3d4a21826d4fd" in combined
    assert "https://guillaumejaume.github.io/FUNSD/dataset.zip" in combined
    assert "doc-analysis/XFUND" in combined
    assert "18504926" in combined
    assert "18786808" in combined
    assert "aharley/rvl_cdip" in combined
    assert "historical_url_replacements" in combined
    assert 'replacement_count != 4' in combined
    assert 'str(patched_script)' in combined
    assert "claim_id" not in combined
