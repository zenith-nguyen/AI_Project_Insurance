"""Build the one-shot CarDD final-test notebook for the locked YOLOv8s model."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/CarDD_YOLOv8s_Final_Test_Acc2_v1.ipynb")


def markdown(value: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in value.strip().splitlines()],
    }


def code(value: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in value.strip().splitlines()],
    }


def build() -> None:
    cells = [
        markdown(
            """# CarDD YOLOv8s-seg — Final Test v1

Model đã được chọn bằng validation theo quy tắc đặt trước. Notebook này mở test đúng một lần cho checkpoint đã khóa. Nếu report hoặc execution lock đã tồn tại, notebook sẽ dừng và không chạy test lại."""
        ),
        markdown("## 1. Protocol và artifact đã khóa"),
        code(
            """from pathlib import Path

NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
CONVERTED = NEW_PROJECT / "data/processed/cardd_yolo_v1"

RUNS_ROOT = NEW_PROJECT / "artifacts/image"
REPORTS_ROOT = NEW_PROJECT / "reports/metrics"
SELECTION_REPORT = REPORTS_ROOT / "cardd_yolo_model_selection_v1.json"
SELECTED_WEIGHTS = RUNS_ROOT / "cardd_yolov8s_seg_candidate_v1/weights/best.pt"

FINAL_RUN_NAME = "cardd_yolov8s_seg_final_test_v1"
FINAL_RUN_DIR = RUNS_ROOT / "evaluation" / FINAL_RUN_NAME
FINAL_REPORT = REPORTS_ROOT / "cardd_yolov8s_seg_final_test_v1.json"
FINAL_LOCK = REPORTS_ROOT / "cardd_yolov8s_seg_final_test_v1.execution.json"

EXPECTED_CHECKPOINT_SHA256 = "6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b"
EXPECTED_SELECTION_DELTA = 0.010865255144515196
EXPECTED_TEST_IMAGES = 419
EXPECTED_TEST_INSTANCES = 931
RUN_FINAL_TEST = True

print("Final-test protocol loaded.")
print("Locked checkpoint SHA-256:", EXPECTED_CHECKPOINT_SHA256)
print("Expected test images:", EXPECTED_TEST_IMAGES)
print("RUN_FINAL_TEST:", RUN_FINAL_TEST)"""
        ),
        markdown("## 2. GPU, Drive và môi trường"),
        code(
            """import importlib
import subprocess
import sys

import torch
from google.colab import drive

if not Path("/content/drive/MyDrive").is_dir():
    drive.mount("/content/drive")

if not torch.cuda.is_available():
    raise RuntimeError("Hãy chọn Runtime → Change runtime type → T4 GPU.")

try:
    from ultralytics import YOLO
except ModuleNotFoundError:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "ultralytics==8.4.173",
            "PyYAML>=6,<7",
            "Pillow>=10,<13",
            "tqdm>=4.66,<5",
        ],
        check=True,
    )
    importlib.invalidate_caches()
    from ultralytics import YOLO

import importlib.metadata as metadata
import yaml

print("GPU:", torch.cuda.get_device_name(0))
print("Ultralytics:", metadata.version("ultralytics"))
print("Environment: PASS")"""
        ),
        markdown("## 3. Xác minh model selection và checkpoint"),
        code(
            """import hashlib
import json
from datetime import datetime, timezone


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


required = [
    SOURCE_CARDD / "data",
    CONVERTED / "split_manifest.jsonl",
    CONVERTED / "conversion_report.json",
    CONVERTED / "labels/test",
    SELECTION_REPORT,
    SELECTED_WEIGHTS,
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise FileNotFoundError("Thiếu artifact bắt buộc:\\n" + "\\n".join(missing))

selection = json.loads(SELECTION_REPORT.read_text(encoding="utf-8"))
actual_checkpoint_hash = sha256_file(SELECTED_WEIGHTS)

selection_checks = {
    "selected_model": selection.get("selected_model") == "yolov8s-seg candidate v1",
    "checkpoint_hash_in_selection": selection.get("selected_checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA256,
    "checkpoint_hash_on_drive": actual_checkpoint_hash == EXPECTED_CHECKPOINT_SHA256,
    "selection_delta": abs(float(selection.get("candidate_delta")) - EXPECTED_SELECTION_DELTA) < 1e-12,
    "test_not_used_for_selection": selection.get("test_split_used") is False,
    "final_test_was_locked": selection.get("final_test_locked") is True,
}
failed_checks = [name for name, passed in selection_checks.items() if not passed]
if failed_checks:
    raise RuntimeError("Model-selection lock không hợp lệ: " + ", ".join(failed_checks))

print(json.dumps(selection_checks, indent=2))
print("Model and checkpoint lock: PASS")"""
        ),
        markdown("## 4. Dựng test view sau khi model đã khóa"),
        code(
            """import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm.auto import tqdm

LOCAL_TEST = Path("/content/cardd_yolov8s_final_test_v1")
BUILDING_TEST = Path("/content/cardd_yolov8s_final_test_v1.building")

conversion_report = json.loads(
    (CONVERTED / "conversion_report.json").read_text(encoding="utf-8")
)
all_manifest_rows = [
    json.loads(line)
    for line in (CONVERTED / "split_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
test_rows = [row for row in all_manifest_rows if row["split"] == "test"]
if len(test_rows) != EXPECTED_TEST_IMAGES:
    raise RuntimeError(f"Test manifest có {len(test_rows)} ảnh, expected {EXPECTED_TEST_IMAGES}")


def copy_if_needed(source: Path, destination: Path) -> bool:
    source_size = source.stat().st_size
    if destination.is_file() and destination.stat().st_size == source_size:
        return True
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    partial.unlink(missing_ok=True)
    last_error = None
    for attempt in range(1, 4):
        try:
            shutil.copyfile(source, partial)
            if partial.stat().st_size != source_size:
                raise IOError(f"Sai kích thước sau khi copy: {source.name}")
            os.replace(partial, destination)
            return False
        except Exception as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Không copy được {source}: {last_error}")


def stage_one(row: dict) -> bool:
    image_name = row["image"]
    source_image = SOURCE_CARDD / "data" / image_name
    source_label = CONVERTED / "labels/test" / f"{Path(image_name).stem}.txt"
    if not source_image.is_file() or not source_label.is_file():
        raise FileNotFoundError(f"Thiếu test image/label: {image_name}")
    reused = copy_if_needed(source_image, BUILDING_TEST / "images/test" / image_name)
    copy_if_needed(source_label, BUILDING_TEST / "labels/test" / source_label.name)
    return reused


def test_counts(root: Path) -> dict:
    return {
        "images": len(list((root / "images/test").glob("*.jpg"))),
        "labels": len(list((root / "labels/test").glob("*.txt"))),
    }


def complete_test_view(root: Path) -> bool:
    counts = test_counts(root) if root.is_dir() else {"images": 0, "labels": 0}
    return counts == {"images": EXPECTED_TEST_IMAGES, "labels": EXPECTED_TEST_IMAGES}


if complete_test_view(LOCAL_TEST) and (LOCAL_TEST / "data.yaml").is_file():
    print("Local final-test view đã hoàn chỉnh; sử dụng lại.")
else:
    if LOCAL_TEST.exists():
        raise RuntimeError("Local final-test view tồn tại nhưng không hoàn chỉnh; restart runtime.")
    BUILDING_TEST.mkdir(parents=True, exist_ok=True)
    failures = []
    reused = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(stage_one, row): row for row in test_rows}
        with tqdm(total=len(futures), desc="Staging final test", unit="image") as progress:
            for future in as_completed(futures):
                row = futures[future]
                try:
                    reused += int(future.result())
                except Exception as error:
                    failures.append({"image": row.get("image"), "error": repr(error)})
                progress.update(1)
    if failures:
        raise RuntimeError(f"Có {len(failures)} test file không copy được: {failures[:3]}")
    if not complete_test_view(BUILDING_TEST):
        raise RuntimeError(f"Final-test view chưa đủ: {test_counts(BUILDING_TEST)}")

    # Ultralytics requires train/val keys while loading a detection dataset.
    # These are compatibility aliases only; the evaluation call below uses split='test'.
    data_payload = {
        "path": str(LOCAL_TEST),
        "train": "images/test",
        "val": "images/test",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(conversion_report["classes"])},
    }
    (BUILDING_TEST / "data.yaml").write_text(
        yaml.safe_dump(data_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    BUILDING_TEST.replace(LOCAL_TEST)
    print("Files reused from interrupted staging:", reused)

TEST_DATA_YAML = LOCAL_TEST / "data.yaml"
print("Final-test local counts:", test_counts(LOCAL_TEST))
print("Final-test staging: PASS")"""
        ),
        markdown("## 5. Kiểm tra test labels trước khi mở test"),
        code(
            """test_label_files = sorted((LOCAL_TEST / "labels/test").glob("*.txt"))
test_instances = 0
invalid_rows = 0
for label in test_label_files:
    for line in label.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        try:
            class_id = int(parts[0])
            coordinates = [float(value) for value in parts[1:]]
        except (IndexError, ValueError):
            invalid_rows += 1
            continue
        if (
            len(parts) < 7
            or (len(parts) - 1) % 2 != 0
            or class_id not in range(6)
            or any(value < 0 or value > 1 for value in coordinates)
        ):
            invalid_rows += 1
        test_instances += 1

test_validation = {
    "images": test_counts(LOCAL_TEST)["images"],
    "labels": len(test_label_files),
    "instances": test_instances,
    "invalid_rows": invalid_rows,
}
expected_validation = {
    "images": EXPECTED_TEST_IMAGES,
    "labels": EXPECTED_TEST_IMAGES,
    "instances": EXPECTED_TEST_INSTANCES,
    "invalid_rows": 0,
}
if test_validation != expected_validation:
    raise RuntimeError({"actual": test_validation, "expected": expected_validation})

print(json.dumps(test_validation, indent=2))
print("Final-test labels: PASS")"""
        ),
        markdown(
            """## 6. Chạy Final Test đúng một lần

Cell tạo execution lock **trước** khi model đọc test. Nếu runtime ngắt sau thời điểm này, không tự xóa lock hoặc chạy lại; gửi file execution JSON để audit."""
        ),
        code(
            """import traceback
import uuid

if not RUN_FINAL_TEST:
    raise RuntimeError("RUN_FINAL_TEST chưa được mở.")
if FINAL_REPORT.exists():
    raise FileExistsError(
        f"Final-test report đã tồn tại; không chạy lần hai: {FINAL_REPORT}"
    )
if FINAL_LOCK.exists():
    existing_lock = FINAL_LOCK.read_text(encoding="utf-8")
    raise RuntimeError(
        "Execution lock đã tồn tại; không tự chạy lại final test. Nội dung:\\n" + existing_lock
    )
if FINAL_RUN_DIR.exists():
    raise RuntimeError(
        f"Final-test run directory đã tồn tại nhưng chưa có report/lock: {FINAL_RUN_DIR}"
    )

REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
run_id = str(uuid.uuid4())
lock_payload = {
    "run_id": run_id,
    "status": "started",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "split": "test",
    "checkpoint": str(SELECTED_WEIGHTS),
    "checkpoint_sha256": actual_checkpoint_hash,
    "selection_report": str(SELECTION_REPORT),
    "selection_report_sha256": sha256_file(SELECTION_REPORT),
    "test_images": EXPECTED_TEST_IMAGES,
    "test_instances": EXPECTED_TEST_INSTANCES,
}
FINAL_LOCK.write_text(
    json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Final-test execution lock created:", FINAL_LOCK)

try:
    test_metrics = YOLO(str(SELECTED_WEIGHTS)).val(
        data=str(TEST_DATA_YAML),
        split="test",
        imgsz=640,
        batch=8,
        device=0,
        project=str(RUNS_ROOT / "evaluation"),
        name=FINAL_RUN_NAME,
        plots=True,
        verbose=True,
        exist_ok=False,
    )
    final_report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "protocol": "locked model; one-shot final test",
        "model": "yolov8s-seg candidate v1",
        "weights": str(SELECTED_WEIGHTS),
        "weights_sha256": actual_checkpoint_hash,
        "selection_report": str(SELECTION_REPORT),
        "selection_report_sha256": sha256_file(SELECTION_REPORT),
        "split": "test",
        "test_run_number": 1,
        "images": EXPECTED_TEST_IMAGES,
        "instances": EXPECTED_TEST_INSTANCES,
        "class_names": {str(key): value for key, value in test_metrics.names.items()},
        "mask": {
            "map50_95": float(test_metrics.seg.map),
            "map50": float(test_metrics.seg.map50),
            "map75": float(test_metrics.seg.map75),
            "per_class_map50_95": test_metrics.seg.maps.tolist(),
        },
        "box": {
            "map50_95": float(test_metrics.box.map),
            "map50": float(test_metrics.box.map50),
            "map75": float(test_metrics.box.map75),
            "per_class_map50_95": test_metrics.box.maps.tolist(),
        },
        "speed_ms_per_image": dict(test_metrics.speed),
        "run_directory": str(test_metrics.save_dir),
    }
    temporary_report = FINAL_REPORT.with_suffix(".json.tmp")
    temporary_report.write_text(
        json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_report.replace(FINAL_REPORT)
    lock_payload.update(
        {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "final_report": str(FINAL_REPORT),
            "final_report_sha256": sha256_file(FINAL_REPORT),
        }
    )
    FINAL_LOCK.write_text(
        json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
except BaseException as error:
    lock_payload.update(
        {
            "status": "failed_or_interrupted",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
    )
    FINAL_LOCK.write_text(
        json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    raise

print()
print("=== FINAL TEST COMPLETED EXACTLY ONCE ===")
print("Mask mAP50-95:", final_report["mask"]["map50_95"])
print("Mask mAP50:", final_report["mask"]["map50"])
print("Box mAP50-95:", final_report["box"]["map50_95"])
print("Final report:", FINAL_REPORT)
print("Execution record:", FINAL_LOCK)"""
        ),
        markdown(
            """## 7. Sau khi hoàn tất

Gửi output `FINAL TEST COMPLETED EXACTLY ONCE` hoặc file `cardd_yolov8s_seg_final_test_v1.json`. Không chạy lại notebook sau khi report đã tồn tại."""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "T4", "name": OUTPUT.name, "provenance": []},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
