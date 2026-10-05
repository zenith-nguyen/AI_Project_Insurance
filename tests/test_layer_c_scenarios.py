import csv

from PIL import Image

from reports.handoff.layer_c_scenario_script import generate_variants


def test_layer_c_generator_creates_four_outputs_per_image(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    Image.new("RGB", (100, 80), (200, 10, 10)).save(input_dir / "one.jpg")
    Image.new("RGB", (120, 90), (10, 10, 200)).save(input_dir / "two.png")

    summary = generate_variants(input_dir, output_dir, seed=7)

    assert summary["input_images"] == 2
    assert summary["total_outputs"] == 8
    assert all(summary[key] == 2 for key in ("3_plate_swap", "4_screen_recapture", "5_exif_tampering", "8_strip_reencode"))
    with (output_dir / "manifest.csv").open(encoding="utf-8-sig") as stream:
        assert len(list(csv.DictReader(stream))) == 8

    exif_file = next((output_dir / "scenario_05_exif_tampering").glob("*.jpg"))
    stripped_file = next((output_dir / "scenario_08_strip_reencode").glob("*.jpg"))
    with Image.open(exif_file) as image:
        assert image.getexif()[271] == "LAYER_C_SYNTHETIC"
    with Image.open(stripped_file) as image:
        assert len(image.getexif()) == 0
