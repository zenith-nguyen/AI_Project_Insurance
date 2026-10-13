import json

from scripts.evaluate_media_authenticity_benchmark import evaluate


def test_media_benchmark_reports_class_specific_errors(tmp_path):
    rows = [
        {"label": "ai_generated", "split": "test", "source_group": "a", "score": 0.9},
        {"label": "ai_edited", "split": "test", "source_group": "b", "score": 0.2},
        {"label": "camera_original", "split": "test", "source_group": "c", "score": 0.1},
        {"label": "social_reencode", "split": "test", "source_group": "d", "score": 0.8},
    ]
    path = tmp_path / "predictions.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    report = evaluate(path, 0.5)

    assert report["confusion"] == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}
    assert report["precision"] == 0.5
    assert report["recall"] == 0.5
    assert report["by_label"]["social_reencode"]["fp"] == 1
