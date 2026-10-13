from pathlib import Path

from PIL import Image

from scripts.build_media_authenticity_benchmark import build


def make_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (10, 10), color).save(path)


def test_transformed_variants_stay_in_same_split(tmp_path: Path):
    root = tmp_path / "benchmark"
    make_image(root / "camera_original/case-1__original.png", (1, 2, 3))
    make_image(root / "social_reencode/case-1__facebook.png", (2, 3, 4))
    make_image(root / "ai_generated/case-2__generator-a.png", (3, 4, 5))
    output = tmp_path / "manifest.jsonl"

    report = build(root, output)
    rows = [__import__("json").loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    case_one_splits = {row["split"] for row in rows if row["source_group"] == "case-1"}
    assert report["valid"] is True
    assert case_one_splits == {next(iter(case_one_splits))}
    assert report["group_leakage"] == {}
