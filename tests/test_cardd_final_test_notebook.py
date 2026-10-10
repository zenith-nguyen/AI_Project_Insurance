import json
from pathlib import Path

import yaml


NOTEBOOK = Path("notebooks/CarDD_YOLOv8s_Final_Test_Acc2_v1.ipynb")


def notebook_sources() -> tuple[dict, list[str], str]:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    return notebook, code_cells, "\n".join(code_cells)


def test_final_test_notebook_locks_exact_model_and_refuses_second_run():
    notebook, code_cells, combined = notebook_sources()

    assert "AI_Project_Insurance_Acc 2" in combined
    assert "AI_Project_Insurance_OLD" in combined
    assert "6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b" in combined
    assert "EXPECTED_TEST_IMAGES = 419" in combined
    assert "EXPECTED_TEST_INSTANCES = 931" in combined
    assert "RUN_FINAL_TEST = True" in combined
    assert 'split="test"' in combined
    assert '"test_run_number": 1' in combined
    assert "if FINAL_REPORT.exists()" in combined
    assert "if FINAL_LOCK.exists()" in combined
    assert '"status": "started"' in combined
    assert '"status": "completed"' in combined
    assert combined.count(').val(') == 1
    assert "Ã" not in combined
    assert "áº" not in combined

    for index, source in enumerate(code_cells):
        compile(source, f"final_test_cell_{index}", "exec")


def test_final_test_staging_filters_manifest_to_test_only():
    _, _, combined = notebook_sources()

    assert 'test_rows = [row for row in all_manifest_rows if row["split"] == "test"]' in combined
    assert 'CONVERTED / "labels/test"' in combined
    assert 'BUILDING_TEST / "images/test"' in combined
    assert "Model and checkpoint lock: PASS" in combined


def test_final_test_stages_only_test_rows_and_writes_test_yaml(tmp_path):
    _, code_cells, _ = notebook_sources()
    stage_code = next(source for source in code_cells if "def stage_one" in source)

    bronze = tmp_path / "bronze"
    converted = tmp_path / "converted"
    # Replace fixed local paths in the generated cell so this test stays isolated.
    isolated_local = tmp_path / "local_test"
    isolated_building = tmp_path / "local_test.building"
    stage_code = stage_code.replace(
        'Path("/content/cardd_yolov8s_final_test_v1")', f"Path({str(isolated_local)!r})"
    ).replace(
        'Path("/content/cardd_yolov8s_final_test_v1.building")',
        f"Path({str(isolated_building)!r})",
    )

    (bronze / "data").mkdir(parents=True)
    (converted / "labels/test").mkdir(parents=True)
    (bronze / "data/test.jpg").write_bytes(b"test-image")
    (converted / "labels/test/test.txt").write_text(
        "0 0 0 1 0 1 1\n", encoding="utf-8"
    )
    (converted / "split_manifest.jsonl").write_text(
        json.dumps({"image": "test.jpg", "split": "test"}) + "\n",
        encoding="utf-8",
    )
    (converted / "conversion_report.json").write_text(
        json.dumps({"classes": ["damage"]}), encoding="utf-8"
    )

    namespace = {
        "SOURCE_CARDD": bronze,
        "CONVERTED": converted,
        "EXPECTED_TEST_IMAGES": 1,
        "json": json,
        "yaml": yaml,
        "Path": Path,
    }
    exec(stage_code, namespace)

    payload = yaml.safe_load(
        (isolated_local / "data.yaml").read_text(encoding="utf-8")
    )
    assert payload["test"] == "images/test"
    assert (isolated_local / "images/test/test.jpg").read_bytes() == b"test-image"
    assert (isolated_local / "labels/test/test.txt").is_file()
