from PIL import Image

from src.document.ocr import PaddleOCREngine
from src.document.schema import BoundingBox, OCRToken


class FakePaddle:
    def predict(self, path):
        with Image.open(path) as image:
            width, height = image.size
        return [{"res": {"rec_texts": ["Total"], "rec_scores": [0.9], "rec_polys": [[[0, 0], [width, 0], [width, height], [0, height]]]}}]


def test_ocr_resize_scales_boxes_back_to_original_pixels(tmp_path):
    source = tmp_path / "large.png"
    Image.new("RGB", (2000, 1000), "white").save(source)
    engine = PaddleOCREngine.__new__(PaddleOCREngine)
    engine._engine = FakePaddle()
    engine.max_side = 1000
    tokens = engine.predict(source)
    assert tokens == [OCRToken("Total", 0.9, BoundingBox(0, 0, 2000, 1000), 1)]
