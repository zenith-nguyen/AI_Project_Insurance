from pathlib import Path

import pytest

from src.image.evaluate_yolo import evaluate, plain


def test_test_split_requires_explicit_unlock(tmp_path):
    with pytest.raises(PermissionError, match="--allow-test"):
        evaluate(
            tmp_path / "best.pt",
            tmp_path / "data.yaml",
            tmp_path / "metrics.json",
            split="test",
            project=tmp_path / "runs",
            name="test",
        )


def test_plain_converts_nested_metric_values():
    assert plain({"metric": (1, 2.5), "path": Path("x")}) == {
        "metric": [1, 2.5],
        "path": "x",
    }
