from pathlib import Path

from src.baselines.registry import load_baseline_registry


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_registry_covers_every_registered_product_module():
    baseline = load_baseline_registry(ROOT / "configs/baseline_registry.v1.yaml")
    assert set(baseline.modules) == {
        "tabular_risk",
        "damage_segmentation",
        "document_classifier",
        "ocr",
        "document_kie",
        "consistency",
        "relationships",
        "media_authenticity",
    }
    assert baseline.modules["damage_segmentation"]["comparison"]["comparable"] is True
    assert baseline.modules["ocr"]["comparison"]["delta"] is None


def test_baseline_registry_distinguishes_external_and_team_work():
    baseline = load_baseline_registry(ROOT / "configs/baseline_registry.v1.yaml")
    assert baseline.modules["document_classifier"]["baseline"]["origin_type"] == "external_pretrained_team_evaluated"
    assert baseline.modules["document_kie"]["baseline"]["origin_type"] == "team_implemented"
    assert baseline.modules["document_kie"]["current"]["origin_type"] == "team_trained_from_external_weights"
