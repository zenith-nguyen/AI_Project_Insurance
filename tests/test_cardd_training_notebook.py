import json
from pathlib import Path


def test_training_notebook_v2_is_utf8_self_contained_and_compilable():
    path = Path("notebooks/CarDD_YOLOv8_Training_v2.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    combined = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )

    assert "quy trình huấn luyện v2" in combined
    assert "ThreadPoolExecutor" in combined
    assert "BUILDING_DATASET.mkdir(parents=True, exist_ok=True)" in combined
    assert "capture_output=True" not in combined
    assert "RUN_FINAL_TEST = False" in combined
    assert 'runtime_best = globals().get("BEST_WEIGHTS")' in combined
    assert 'cardd_yolov8n_seg_baseline_v2"\n    / "weights"' in combined
    assert "Ã" not in combined
    assert "áº" not in combined

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"cell_{index}", "exec")


def test_training_notebook_v2_stages_and_validates_a_small_dataset(tmp_path):
    path = Path("notebooks/CarDD_YOLOv8_Training_v2.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    stage_code = next(source for source in code_cells if "def copy_if_needed" in source)
    validation_code = next(source for source in code_cells if "def validate_yolo_dataset" in source)

    bronze = tmp_path / "bronze"
    converted = tmp_path / "converted"
    local_dataset = tmp_path / "cardd_yolo_v1"
    building_dataset = tmp_path / "cardd_yolo_v1.building"
    for split in ("train", "val"):
        (converted / "labels" / split).mkdir(parents=True, exist_ok=True)
    (bronze / "data").mkdir(parents=True)

    rows = [
        {"image": "train.jpg", "split": "train"},
        {"image": "val.jpg", "split": "val"},
    ]
    for row in rows:
        (bronze / "data" / row["image"]).write_bytes(b"jpeg-bytes")
        (converted / "labels" / row["split"] / f"{Path(row['image']).stem}.txt").write_text(
            "0 0 0 1 0 1 1\n", encoding="utf-8"
        )

    namespace = {
        "SOURCE_CARDD": bronze,
        "CONVERTED": converted,
        "LOCAL_DATASET": local_dataset,
        "BUILDING_DATASET": building_dataset,
        "NEW_PROJECT": tmp_path / "project",
        "REPORTS_ROOT": tmp_path / "reports",
        "RUNS_ROOT": tmp_path / "runs",
        "EXPECTED_IMAGES": 2,
        "EXPECTED_INSTANCES": 2,
        "EXPECTED_SPLITS": {"train": 1, "val": 1, "test": 0},
        "manifest_rows": rows,
        "report": {"classes": ["damage"]},
    }

    exec(stage_code, namespace)
    exec(validation_code, namespace)

    assert (local_dataset / "data.yaml").is_file()
    assert (local_dataset / "images/train/train.jpg").read_bytes() == b"jpeg-bytes"
    assert (local_dataset / "labels/val/val.txt").is_file()
    assert namespace["validation"]["valid"] is True
