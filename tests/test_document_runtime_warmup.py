from src.document import runtime


class FakeClassifier:
    model_name = "dit-test"
    model_version = "v1"

    def __init__(self, device=None):
        self.device = device


class FakeOCR:
    model_name = "ocr-test"
    model_version = "v1"

    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeKIE:
    model_name = "layout-test"
    model_version = "v1"

    def __init__(self, checkpoint, device=None):
        self.checkpoint = checkpoint

    def extract(self, tokens, image=None):
        return []


def test_document_runtime_warmup_and_cache_key(monkeypatch, tmp_path):
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "config.json").write_text("{}", encoding="utf-8")
    expected_hash = runtime.tree_hash(checkpoint)
    monkeypatch.setattr(runtime, "DiTClassifier", FakeClassifier)
    monkeypatch.setattr(runtime, "PaddleOCREngine", FakeOCR)
    monkeypatch.setattr(runtime, "LayoutLMv3KIE", FakeKIE)
    monkeypatch.setenv("INSURANCE_OCR_PROFILE", "robust")
    monkeypatch.delenv("INSURANCE_OCR_MAX_SIDE", raising=False)

    adapter = runtime.DocumentRuntimeAdapter(checkpoint, expected_tree_hash=expected_hash)
    assert adapter.readiness()["status"] == "not_started"
    adapter.warmup()
    assert adapter.readiness()["status"] == "ready"
    assert adapter.cache_key("evidence-a") == adapter.cache_key("evidence-a")
    assert adapter.cache_key("evidence-a") != adapter.cache_key("evidence-b")


def test_document_cache_key_changes_with_ocr_configuration(monkeypatch, tmp_path):
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "config.json").write_text("{}", encoding="utf-8")
    adapter = runtime.DocumentRuntimeAdapter(
        checkpoint, expected_tree_hash=runtime.tree_hash(checkpoint),
    )
    monkeypatch.setenv("INSURANCE_OCR_PROFILE", "robust")
    robust = adapter.cache_key("evidence-a")
    monkeypatch.setenv("INSURANCE_OCR_PROFILE", "fast_upright")
    assert adapter.cache_key("evidence-a") != robust
