from pathlib import Path

from src.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_all_product_modules_and_public_summary_hides_artifact_locations():
    registry = load_registry(ROOT / "configs/model_registry.v1.yaml")
    assert set(registry.modules) == {
        "tabular_risk",
        "damage_segmentation",
        "document_classifier",
        "ocr",
        "document_kie",
        "consistency",
        "relationships",
    }
    summary = registry.public_summary()
    assert summary["product_version"] == "research-v1"
    assert "artifact_uri" not in summary["models"]["damage_segmentation"]
    assert summary["models"]["document_kie"]["status"] == "final_test_complete"
    assert summary["models"]["document_kie"]["metric_value"] == 0.86593707250342
