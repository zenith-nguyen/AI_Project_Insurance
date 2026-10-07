import json
from pathlib import Path

import yaml


def notebook_source() -> tuple[dict, str]:
    path = Path("notebooks/CarDD_YOLOv8s_Candidate_v1.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    combined = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )
    return notebook, combined


def test_candidate_notebook_is_compilable_and_keeps_test_locked():
    notebook, combined = notebook_source()

    assert "YOLOv8s-seg candidate v1" in combined
    assert 'MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL = 0.01' in combined
    assert 'EXPECTED_BASELINE_MASK_MAP50_95 = 0.5175' in combined
    assert 'RUN_FINAL_TEST = False' in combined
    assert '"test_split_used": False' in combined
    assert '"test": "images/test"' not in combined
    assert 'split="test"' not in combined
    assert 'YOLO("yolov8s-seg.pt").train' in combined
    assert "Ã" not in combined
    assert "áº" not in combined

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"candidate_cell_{index}", "exec")


def test_candidate_notebook_uses_only_train_and_validation_manifest_rows():
    _, combined = notebook_source()

    assert 'row["split"] in EXPECTED_SPLITS' in combined
    assert 'EXPECTED_SPLITS = {"train": 1966, "val": 431}' in combined
    assert 'assert "test:" not in DATA_YAML.read_text' in combined
    assert '"primary_metric": "validation mask mAP50-95"' in combined


def code_cells() -> list[str]:
    notebook, _ = notebook_source()
    return [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


def test_candidate_notebook_stages_only_train_and_validation(tmp_path):
    stage_code = next(source for source in code_cells() if "def copy_if_needed" in source)

    bronze = tmp_path / "bronze"
    converted = tmp_path / "converted"
    local_dataset = tmp_path / "candidate"
    building_dataset = tmp_path / "candidate.building"
    for split in ("train", "val", "test"):
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

    # Test data exists at the source, but candidate staging must never copy it.
    (bronze / "data/test.jpg").write_bytes(b"secret-test-bytes")
    (converted / "labels/test/test.txt").write_text("0 0 0 1 0 1 1\n", encoding="utf-8")

    namespace = {
        "SOURCE_CARDD": bronze,
        "CONVERTED": converted,
        "LOCAL_DATASET": local_dataset,
        "BUILDING_DATASET": building_dataset,
        "REPORTS_ROOT": tmp_path / "reports",
        "EXPECTED_SPLITS": {"train": 1, "val": 1},
        "manifest_rows": rows,
        "conversion_report": {"classes": ["damage"]},
        "yaml": yaml,
        "json": json,
        "Path": Path,
    }

    exec(stage_code, namespace)

    payload = yaml.safe_load((local_dataset / "data.yaml").read_text(encoding="utf-8"))
    assert payload["train"] == "images/train"
    assert payload["val"] == "images/val"
    assert "test" not in payload
    assert not (local_dataset / "images/test").exists()
    assert (local_dataset / "images/train/train.jpg").read_bytes() == b"jpeg-bytes"


def test_candidate_selection_rule_needs_full_minimum_gain(tmp_path):
    selection_code = next(
        source for source in code_cells() if "baseline_score = float" in source
    )

    baseline_weights = tmp_path / "baseline.pt"
    candidate_weights = tmp_path / "candidate.pt"
    baseline_weights.write_bytes(b"baseline")
    candidate_weights.write_bytes(b"candidate")
    baseline_report = {
        "class_names": {
            str(index): name
            for index, name in enumerate(
                ["crack", "dent", "glass shatter", "lamp broken", "scratch", "tire flat"]
            )
        },
        "mask": {
            "map50_95": 0.5175,
            "per_class_map50_95": [0.0649, 0.2960, 0.8721, 0.6590, 0.2636, 0.9496],
        },
    }
    candidate_report = {
        "mask": {
            "map50_95": 0.5274,
            "per_class_map50_95": [0.1, 0.31, 0.87, 0.66, 0.28, 0.95],
        }
    }
    selection_report = tmp_path / "selection.json"

    import hashlib
    from datetime import datetime, timezone

    def sha256_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    namespace = {
        "baseline_report": baseline_report,
        "candidate_report": candidate_report,
        "MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL": 0.01,
        "CANDIDATE_BEST": candidate_weights,
        "BASELINE_WEIGHTS": baseline_weights,
        "CANDIDATE_REPORT": tmp_path / "candidate.json",
        "BASELINE_REPORT": tmp_path / "baseline.json",
        "SELECTION_REPORT": selection_report,
        "sha256_file": sha256_file,
        "datetime": datetime,
        "timezone": timezone,
        "json": json,
    }

    exec(selection_code, namespace)
    selection = json.loads(selection_report.read_text(encoding="utf-8"))

    assert selection["selected_model"] == "yolov8n-seg baseline v2"
    assert selection["final_test_locked"] is True
    assert selection["test_split_used"] is False
