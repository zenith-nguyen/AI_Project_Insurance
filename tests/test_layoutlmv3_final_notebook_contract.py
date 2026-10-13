import json
from pathlib import Path


def test_final_and_recovery_notebooks_define_metric_normalizer():
    root = Path(__file__).resolve().parents[1]
    notebooks = [
        root / "notebooks" / "Document_LayoutLMv3_Final_Test_Acc2_v3.ipynb",
        root / "notebooks" / "Document_LayoutLMv3_Final_Test_Recovery_Acc2_v1.ipynb",
    ]
    for path in notebooks:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])
        assert "def metric_value(field,value):" in source, path.name
        assert source.index("def metric_value(field,value):") < source.index("def compute_metrics(result):")
