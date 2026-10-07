"""Build a resumable Colab notebook for the YOLOv8s CarDD candidate."""
from __future__ import annotations

import json
from pathlib import Path


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


def build(output: Path) -> None:
    cells = [
        markdown(
            """# CarDD YOLOv8s-seg candidate v1

Notebook này chạy đúng một candidate trên train/validation đã khóa. Test split không được tạo trong dataset training và không được đọc. Sau khi candidate hoàn tất, notebook so sánh với YOLOv8n baseline và ghi đề xuất lựa chọn; final test vẫn khóa."""
        ),
        markdown("## 1. Cấu hình và quy tắc lựa chọn đã khóa trước"),
        code(
            """from pathlib import Path

OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance")
SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
CONVERTED = NEW_PROJECT / "data/processed/cardd_yolo_v1"

LOCAL_DATASET = Path("/content/cardd_yolov8s_candidate_data")
BUILDING_DATASET = Path("/content/cardd_yolov8s_candidate_data.building")
RUNS_ROOT = NEW_PROJECT / "artifacts/image"
REPORTS_ROOT = NEW_PROJECT / "reports/metrics"

BASELINE_NAME = "cardd_yolov8n_seg_baseline_v2"
CANDIDATE_NAME = "cardd_yolov8s_seg_candidate_v1"
BASELINE_REPORT = REPORTS_ROOT / "cardd_yolov8n_seg_val_v2.json"
CANDIDATE_REPORT = REPORTS_ROOT / "cardd_yolov8s_seg_val_candidate_v1.json"
SELECTION_REPORT = REPORTS_ROOT / "cardd_yolo_model_selection_v1.json"

EXPECTED_SPLITS = {"train": 1966, "val": 431}
EXPECTED_INSTANCES = {"train": 4345, "val": 935}
EXPECTED_BASELINE_MASK_MAP50_95 = 0.5175
EXPECTED_BASELINE_CLASS_MAPS = [0.0649, 0.2960, 0.8721, 0.6590, 0.2636, 0.9496]
SEED = 20261007

# Candidate lớn hơn chỉ được chọn nếu tăng ít nhất 0,01 mask mAP50-95.
# Đây là quy tắc quyết định được đặt trước khi đọc kết quả candidate.
MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL = 0.01
RUN_FINAL_TEST = False

print("Candidate protocol loaded.")
print("Primary metric: validation mask mAP50-95")
print("Minimum gain for larger model:", MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL)
print("Final test locked:", not RUN_FINAL_TEST)"""
        ),
        markdown("## 2. GPU, Drive và môi trường"),
        code(
            """import importlib
import subprocess
import sys

import torch

if not torch.cuda.is_available():
    raise RuntimeError("Hãy chọn Runtime → Change runtime type → T4 GPU.")

print("GPU:", torch.cuda.get_device_name(0))
print("GPU memory GB:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))

from google.colab import drive

if not Path("/content/drive/MyDrive").is_dir():
    drive.mount("/content/drive")

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

print("Ultralytics:", metadata.version("ultralytics"))
print("Environment: PASS")"""
        ),
        markdown("## 3. Kiểm tra input và baseline"),
        code(
            """import json

MANIFEST_PATH = CONVERTED / "split_manifest.jsonl"
CONVERSION_REPORT_PATH = CONVERTED / "conversion_report.json"
BASELINE_WEIGHTS = RUNS_ROOT / BASELINE_NAME / "weights/best.pt"

required_paths = [
    SOURCE_CARDD / "data",
    MANIFEST_PATH,
    CONVERSION_REPORT_PATH,
    CONVERTED / "labels/train",
    CONVERTED / "labels/val",
    BASELINE_WEIGHTS,
    BASELINE_REPORT,
]
missing = [str(path) for path in required_paths if not path.exists()]
if missing:
    raise FileNotFoundError("Thiếu input bắt buộc:\\n" + "\\n".join(missing))

conversion_report = json.loads(CONVERSION_REPORT_PATH.read_text(encoding="utf-8"))
baseline_report = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
all_manifest_rows = [
    json.loads(line)
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
manifest_rows = [row for row in all_manifest_rows if row["split"] in EXPECTED_SPLITS]

actual_manifest_splits = {
    split: sum(row["split"] == split for row in manifest_rows)
    for split in EXPECTED_SPLITS
}
assert actual_manifest_splits == EXPECTED_SPLITS, actual_manifest_splits
assert baseline_report["split"] == "val"
assert baseline_report["test_split_used"] is False
assert round(float(baseline_report["mask"]["map50_95"]), 4) == EXPECTED_BASELINE_MASK_MAP50_95
assert [
    round(float(value), 4)
    for value in baseline_report["mask"]["per_class_map50_95"]
] == EXPECTED_BASELINE_CLASS_MAPS

print("Train/validation manifest:", actual_manifest_splits)
print("Baseline mask mAP50-95:", baseline_report["mask"]["map50_95"])
print("Baseline checkpoint:", BASELINE_WEIGHTS)
print("Input preflight: PASS")"""
        ),
        markdown(
            """## 4. Stage train/validation vào `/content`

Chỉ train và validation được copy; test không xuất hiện trong data YAML. Nếu cell bị ngắt nhưng runtime vẫn còn, chạy lại cell để tiếp tục từ các file đủ kích thước trong `.building`. Nếu Colab cấp runtime mới thì `/content` đã bị xóa và notebook sẽ stage lại từ đầu."""
        ),
        code(
            """import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm.auto import tqdm


def copy_if_needed(source: Path, destination: Path) -> tuple[bool, int]:
    source_size = source.stat().st_size
    if destination.is_file() and destination.stat().st_size == source_size:
        return True, source_size

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
            return False, source_size
        except Exception as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Không copy được {source}: {last_error}")


def stage_one(row: dict) -> tuple[bool, int]:
    image_name = row["image"]
    split = row["split"]
    source_image = SOURCE_CARDD / "data" / image_name
    source_label = CONVERTED / "labels" / split / f"{Path(image_name).stem}.txt"
    if not source_image.is_file() or not source_label.is_file():
        raise FileNotFoundError(f"Thiếu ảnh hoặc label: {image_name}")
    reused, image_bytes = copy_if_needed(
        source_image,
        BUILDING_DATASET / "images" / split / image_name,
    )
    copy_if_needed(
        source_label,
        BUILDING_DATASET / "labels" / split / source_label.name,
    )
    return reused, image_bytes


def split_counts(root: Path) -> dict:
    return {
        split: {
            "images": len(list((root / "images" / split).glob("*.jpg"))),
            "labels": len(list((root / "labels" / split).glob("*.txt"))),
        }
        for split in EXPECTED_SPLITS
    }


def complete_view(root: Path) -> bool:
    if not root.is_dir():
        return False
    counts = split_counts(root)
    return all(
        counts[split]["images"] == expected
        and counts[split]["labels"] == expected
        for split, expected in EXPECTED_SPLITS.items()
    )


if complete_view(LOCAL_DATASET):
    print("Local train/validation dataset đã hoàn chỉnh; sử dụng lại.")
else:
    if LOCAL_DATASET.exists():
        raise RuntimeError(
            "Local dataset tồn tại nhưng không hoàn chỉnh. Restart runtime rồi chạy lại notebook."
        )
    BUILDING_DATASET.mkdir(parents=True, exist_ok=True)
    reused = 0
    failures = []
    print("Bắt đầu/resume copy train + validation. Không dừng khi progress còn tăng.")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(stage_one, row): row for row in manifest_rows}
        with tqdm(total=len(futures), desc="Staging candidate", unit="image") as progress:
            for future in as_completed(futures):
                row = futures[future]
                try:
                    was_reused, _ = future.result()
                    reused += int(was_reused)
                except Exception as error:
                    failures.append({"image": row.get("image"), "error": repr(error)})
                progress.update(1)
                if progress.n % 100 == 0:
                    progress.set_postfix(reused=reused, failures=len(failures))

    if failures:
        failure_report = REPORTS_ROOT / "cardd_yolov8s_staging_failures.json"
        REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
        failure_report.write_text(json.dumps(failures, indent=2), encoding="utf-8")
        raise RuntimeError(
            f"Có {len(failures)} file lỗi. Chạy lại cell để thử tiếp. Report: {failure_report}"
        )

    if not complete_view(BUILDING_DATASET):
        raise RuntimeError(f"Dataset chưa đủ: {split_counts(BUILDING_DATASET)}")

    data_payload = {
        "path": str(LOCAL_DATASET),
        "train": "images/train",
        "val": "images/val",
        "names": {
            index: name
            for index, name in enumerate(conversion_report["classes"])
        },
    }
    (BUILDING_DATASET / "data.yaml").write_text(
        yaml.safe_dump(data_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    BUILDING_DATASET.replace(LOCAL_DATASET)
    print("Files reused from interrupted staging:", reused)

DATA_YAML = LOCAL_DATASET / "data.yaml"
assert DATA_YAML.is_file()
assert "test:" not in DATA_YAML.read_text(encoding="utf-8")
print("Local counts:", split_counts(LOCAL_DATASET))
print("Test path absent from candidate YAML: PASS")
print("Dataset staging: PASS")"""
        ),
        markdown("## 5. Kiểm tra polygon trước training"),
        code(
            """validation_summary = {"splits": {}, "errors": []}
for split, expected_images in EXPECTED_SPLITS.items():
    labels = sorted((LOCAL_DATASET / "labels" / split).glob("*.txt"))
    instances = 0
    invalid_rows = 0
    for label in labels:
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
            instances += 1
    validation_summary["splits"][split] = {
        "images": expected_images,
        "labels": len(labels),
        "instances": instances,
        "invalid_rows": invalid_rows,
    }
    if len(labels) != expected_images or instances != EXPECTED_INSTANCES[split] or invalid_rows:
        validation_summary["errors"].append(split)

if validation_summary["errors"]:
    raise RuntimeError(validation_summary)
print(json.dumps(validation_summary, ensure_ascii=False, indent=2))
print("Candidate dataset validation: PASS")"""
        ),
        markdown(
            """## 6. Train hoặc resume YOLOv8s-seg

Checkpoint được lưu trực tiếp trên Drive. Nếu Colab ngắt, mở lại notebook và Run all; candidate sẽ resume từ `last.pt`."""
        ),
        code(
            """import hashlib
from datetime import datetime, timezone

CANDIDATE_DIR = RUNS_ROOT / CANDIDATE_NAME
CANDIDATE_BEST = CANDIDATE_DIR / "weights/best.pt"
CANDIDATE_LAST = CANDIDATE_DIR / "weights/last.pt"
CANDIDATE_MANIFEST = CANDIDATE_DIR / "candidate_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_candidate_manifest() -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "validation-only candidate comparison",
        "model": "yolov8s-seg.pt",
        "data": str(DATA_YAML),
        "epochs": 100,
        "image_size": 640,
        "batch": 8,
        "patience": 20,
        "seed": SEED,
        "test_split_used": False,
        "best_checkpoint": str(CANDIDATE_BEST),
        "best_checkpoint_sha256": sha256_file(CANDIDATE_BEST),
    }
    CANDIDATE_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if CANDIDATE_MANIFEST.is_file() and CANDIDATE_BEST.is_file():
    saved_manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    actual_best_hash = sha256_file(CANDIDATE_BEST)
    if saved_manifest.get("best_checkpoint_sha256") != actual_best_hash:
        raise RuntimeError("Hash best.pt không khớp candidate_manifest.json")
    if saved_manifest.get("test_split_used") is not False:
        raise RuntimeError("Candidate manifest không xác nhận test đã được khóa")
    print("Candidate đã hoàn tất; sử dụng lại:", CANDIDATE_BEST)
elif CANDIDATE_LAST.is_file():
    print("Resume candidate từ:", CANDIDATE_LAST)
    YOLO(str(CANDIDATE_LAST)).train(resume=True)
    if not CANDIDATE_BEST.is_file():
        raise RuntimeError("Resume kết thúc nhưng không có best.pt")
    write_candidate_manifest()
else:
    if CANDIDATE_DIR.exists():
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = CANDIDATE_DIR.with_name(CANDIDATE_DIR.name + "_incomplete_" + suffix)
        shutil.move(str(CANDIDATE_DIR), str(archived))
        print("Đã lưu run không có checkpoint tại:", archived)

    YOLO("yolov8s-seg.pt").train(
        data=str(DATA_YAML),
        project=str(RUNS_ROOT),
        name=CANDIDATE_NAME,
        epochs=100,
        imgsz=640,
        batch=8,
        patience=20,
        workers=2,
        seed=SEED,
        deterministic=True,
        device=0,
        fraction=1.0,
        save_period=10,
        cache=False,
        amp=True,
        plots=True,
        exist_ok=False,
        verbose=True,
    )
    if not CANDIDATE_BEST.is_file():
        raise RuntimeError("Candidate kết thúc nhưng không có best.pt")
    write_candidate_manifest()

print("Candidate training: PASS")
print("Best checkpoint:", CANDIDATE_BEST)
print("Checkpoint SHA-256:", sha256_file(CANDIDATE_BEST))"""
        ),
        markdown("## 7. Đánh giá candidate trên validation"),
        code(
            """candidate_report = None
if CANDIDATE_REPORT.is_file():
    candidate_report = json.loads(CANDIDATE_REPORT.read_text(encoding="utf-8"))
    report_matches_checkpoint = (
        candidate_report.get("weights_sha256") == sha256_file(CANDIDATE_BEST)
        and candidate_report.get("split") == "val"
        and candidate_report.get("test_split_used") is False
    )
    if report_matches_checkpoint:
        print("Sử dụng candidate report đã có:", CANDIDATE_REPORT)
    else:
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        stale_report = CANDIDATE_REPORT.with_name(
            CANDIDATE_REPORT.stem + "_stale_" + suffix + ".json"
        )
        CANDIDATE_REPORT.replace(stale_report)
        candidate_report = None
        print("Đã lưu report cũ không khớp tại:", stale_report)

if candidate_report is None:
    metrics = YOLO(str(CANDIDATE_BEST)).val(
        data=str(DATA_YAML),
        split="val",
        imgsz=640,
        batch=8,
        device=0,
        project=str(RUNS_ROOT / "evaluation"),
        name="cardd_yolov8s_seg_val_candidate_v1",
        plots=True,
        verbose=True,
        exist_ok=True,
    )
    candidate_report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "weights": str(CANDIDATE_BEST),
        "weights_sha256": sha256_file(CANDIDATE_BEST),
        "split": "val",
        "test_split_used": False,
        "class_names": {str(key): value for key, value in metrics.names.items()},
        "mask": {
            "map50_95": float(metrics.seg.map),
            "map50": float(metrics.seg.map50),
            "map75": float(metrics.seg.map75),
            "per_class_map50_95": metrics.seg.maps.tolist(),
        },
        "box": {
            "map50_95": float(metrics.box.map),
            "map50": float(metrics.box.map50),
            "map75": float(metrics.box.map75),
            "per_class_map50_95": metrics.box.maps.tolist(),
        },
        "run_directory": str(metrics.save_dir),
    }
    temporary = CANDIDATE_REPORT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(candidate_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(CANDIDATE_REPORT)

print("Candidate mask mAP50-95:", candidate_report["mask"]["map50_95"])
print("Candidate report:", CANDIDATE_REPORT)"""
        ),
        markdown("## 8. So sánh và khóa đề xuất lựa chọn"),
        code(
            """baseline_score = float(baseline_report["mask"]["map50_95"])
candidate_score = float(candidate_report["mask"]["map50_95"])
gain = candidate_score - baseline_score

if gain >= MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL:
    selected_model = "yolov8s-seg candidate v1"
    selected_checkpoint = CANDIDATE_BEST
    selected_report = CANDIDATE_REPORT
    reason = (
        f"Candidate tăng {gain:.4f} mask mAP50-95, đạt ngưỡng "
        f"{MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL:.4f}."
    )
else:
    selected_model = "yolov8n-seg baseline v2"
    selected_checkpoint = BASELINE_WEIGHTS
    selected_report = BASELINE_REPORT
    reason = (
        f"Candidate chỉ thay đổi {gain:.4f} mask mAP50-95, chưa đạt ngưỡng "
        f"{MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL:.4f}; giữ mô hình nhỏ hơn."
    )

class_names = [baseline_report["class_names"][str(i)] for i in range(6)]
comparison_rows = []
for index, class_name in enumerate(class_names):
    baseline_class = float(baseline_report["mask"]["per_class_map50_95"][index])
    candidate_class = float(candidate_report["mask"]["per_class_map50_95"][index])
    comparison_rows.append(
        {
            "class": class_name,
            "baseline": baseline_class,
            "candidate": candidate_class,
            "delta": candidate_class - baseline_class,
        }
    )

selection = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "primary_metric": "validation mask mAP50-95",
    "minimum_gain_for_larger_model": MIN_ABSOLUTE_GAIN_FOR_LARGER_MODEL,
    "baseline_mask_map50_95": baseline_score,
    "candidate_mask_map50_95": candidate_score,
    "candidate_delta": gain,
    "per_class_mask_map50_95": comparison_rows,
    "selected_model": selected_model,
    "selected_checkpoint": str(selected_checkpoint),
    "selected_checkpoint_sha256": sha256_file(selected_checkpoint),
    "selected_validation_report": str(selected_report),
    "reason": reason,
    "test_split_used": False,
    "final_test_locked": True,
}
SELECTION_REPORT.write_text(
    json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps(selection, ensure_ascii=False, indent=2))
print()
print("=== MODEL SELECTION READY FOR REVIEW ===")
print("Selected model:", selected_model)
print("Selected checkpoint:", selected_checkpoint)
print("Reason:", reason)
print("Final test remains locked: PASS")
print("Selection report:", SELECTION_REPORT)"""
        ),
        markdown(
            """## 9. Dừng trước final test

Không sửa `RUN_FINAL_TEST` trong notebook candidate. Gửi output phần **MODEL SELECTION READY FOR REVIEW** hoặc file `cardd_yolo_model_selection_v1.json` để kiểm tra. Sau khi model và checkpoint được xác nhận, final test mới được chạy đúng một lần bằng cell riêng."""
        ),
        code(
            """RUN_FINAL_TEST = False
assert RUN_FINAL_TEST is False
print("Final test locked: PASS")
print("Test split was not included in candidate data.yaml.")
print("Send this report for review:", SELECTION_REPORT)"""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "T4", "provenance": []},
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build(Path("notebooks/CarDD_YOLOv8s_Candidate_v1.ipynb"))
