import hashlib
from pathlib import Path

import pytest

from src.image.inference import YOLODamageAdapter


class TensorValue:
    def __init__(self, value): self.value = value
    def item(self): return self.value
    def tolist(self): return self.value


class Boxes:
    cls = [TensorValue(2)]
    conf = [TensorValue(0.91)]
    xyxy = [TensorValue([1, 2, 30, 40])]
    def __len__(self): return 1


class Polygon:
    def tolist(self): return [[1, 2], [30, 2], [30, 40]]


class Result:
    names = {2: "scratch"}
    boxes = Boxes()
    masks = type("Masks", (), {"xy": [Polygon()]})()


class Model:
    def predict(self, **kwargs):
        assert kwargs["conf"] == 0.25
        return [Result()]


def test_yolo_adapter_checks_hash_and_normalizes_detection(tmp_path: Path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"registered checkpoint")
    expected = hashlib.sha256(weights.read_bytes()).hexdigest()
    adapter = YOLODamageAdapter(weights, expected_sha256=expected, model=Model())
    result = adapter.predict(tmp_path / "damage.jpg")
    assert result[0]["class_name"] == "scratch"
    assert result[0]["confidence"] == pytest.approx(0.91)
    assert result[0]["mask_polygon"]


def test_yolo_adapter_rejects_wrong_checkpoint(tmp_path: Path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"wrong")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        YOLODamageAdapter(weights, expected_sha256="0" * 64, model=Model())
