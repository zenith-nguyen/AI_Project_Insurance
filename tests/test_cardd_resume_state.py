import json

from scripts.check_cardd_resume_state import inspect


def test_resume_state_recognizes_complete_bronze_and_conversion(tmp_path):
    project = tmp_path / "project"
    bronze = project / "data/bronze/layerA_cardd"
    processed = project / "data/processed/cardd_yolo_v1"
    (bronze / "data").mkdir(parents=True)
    for name in ("one.jpg", "two.jpg"):
        (bronze / "data" / name).write_bytes(b"image")
    samples = {"samples": [{"filepath": "data/one.jpg"}, {"filepath": "data/two.jpg"}]}
    samples_path = bronze / "samples.json"
    samples_path.write_text(json.dumps(samples), encoding="utf-8")

    rows = [
        {"image": "one.jpg", "split": "train", "instances": 1},
        {"image": "two.jpg", "split": "val", "instances": 1},
    ]
    for row in rows:
        split, stem = row["split"], row["image"].removesuffix(".jpg")
        (processed / "labels" / split).mkdir(parents=True, exist_ok=True)
        (processed / "images" / split).mkdir(parents=True, exist_ok=True)
        (processed / "labels" / split / f"{stem}.txt").write_text("0 0 0 1 0 1 1\n")
        (processed / "images" / split / row["image"]).write_bytes(b"image")
    (processed / "split_manifest.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    from scripts.check_cardd_resume_state import sha256

    (processed / "conversion_report.json").write_text(
        json.dumps({
            "images": 2,
            "split_images": {"train": 1, "val": 1},
            "samples_json_sha256": sha256(samples_path),
            "image_materialization_modes": {"copy": 2},
        }),
        encoding="utf-8",
    )

    result = inspect(project)

    assert result["bronze"]["ready"] is True
    assert result["conversion"]["metadata_ready"] is True
    assert result["resume"]["ready_to_materialize"] is True
    assert result["resume"]["safe_cleanup_candidate"] is True
