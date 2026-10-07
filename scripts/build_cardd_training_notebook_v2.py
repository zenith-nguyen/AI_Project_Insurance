"""Build the self-contained, resumable Colab notebook for CarDD training."""
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
            """# CarDD YOLOv8-seg — quy trình huấn luyện v2

Notebook này chạy độc lập, không cần upload bundle hay vá thêm script. Quy trình gồm: kiểm tra môi trường → kiểm tra dữ liệu → dựng dataset tạm có thể tiếp tục nếu bị ngắt → validation → smoke test → baseline → đánh giá validation.

Trước khi chạy, chọn **Runtime → Change runtime type → T4 GPU**. Không mở test set cho tới khi checkpoint và lựa chọn mô hình đã được khóa."""
        ),
        markdown(
            """## 1. Cấu hình

Các đường dẫn dưới đây khớp với Drive mới và shortcut Drive cũ đã tạo. Có thể chạy lại notebook từ đầu; bước dựng dữ liệu và huấn luyện đều có cơ chế dùng lại hoặc resume."""
        ),
        code(
            """from pathlib import Path

OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance")

SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
CONVERTED = NEW_PROJECT / "data/processed/cardd_yolo_v1"
LOCAL_DATASET = Path("/content/cardd_yolo_v1")
BUILDING_DATASET = Path("/content/cardd_yolo_v1.building")

RUNS_ROOT = NEW_PROJECT / "artifacts/image"
REPORTS_ROOT = NEW_PROJECT / "reports/metrics"

EXPECTED_IMAGES = 2816
EXPECTED_INSTANCES = 6211
EXPECTED_SPLITS = {"train": 1966, "val": 431, "test": 419}
EXPECTED_SAMPLES_SHA256 = "eedd41697824ed5f4afbb87825f5afb40af865d50c314c328565139f8eb994f5"
SEED = 20261007

# Baseline sẽ tự chạy sau khi smoke test đạt yêu cầu.
RUN_BASELINE = True

# Giữ False cho tới khi nhóm đã khóa model/checkpoint.
RUN_FINAL_TEST = False

print("Configuration loaded.")"""
        ),
        markdown("## 2. Kiểm tra GPU và gắn Google Drive"),
        code(
            """import sys
import torch

print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise RuntimeError("Hãy chuyển runtime sang T4 GPU rồi chạy lại notebook từ đầu.")

print("GPU:", torch.cuda.get_device_name(0))
print("GPU memory (GB):", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))"""
        ),
        code(
            """from google.colab import drive

drive.mount("/content/drive")
print("Google Drive mounted.")"""
        ),
        markdown("## 3. Cài môi trường đã cố định phiên bản"),
        code(
            """import subprocess
import sys

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

import importlib.metadata as metadata

print("Ultralytics:", metadata.version("ultralytics"))
print("PyYAML:", metadata.version("PyYAML"))
print("Pillow:", metadata.version("Pillow"))
print("Environment installation: PASS")"""
        ),
        markdown("## 4. Kiểm tra Bronze, labels và split manifest"),
        code(
            """import hashlib
import json

required_paths = [
    SOURCE_CARDD,
    SOURCE_CARDD / "data",
    SOURCE_CARDD / "samples.json",
    CONVERTED / "conversion_report.json",
    CONVERTED / "split_manifest.jsonl",
    CONVERTED / "labels",
]

missing = [str(path) for path in required_paths if not path.exists()]
if missing:
    raise FileNotFoundError("Thiếu dữ liệu bắt buộc:\\n" + "\\n".join(missing))

samples_hash = hashlib.sha256((SOURCE_CARDD / "samples.json").read_bytes()).hexdigest()
report = json.loads((CONVERTED / "conversion_report.json").read_text(encoding="utf-8"))
manifest_rows = [
    json.loads(line)
    for line in (CONVERTED / "split_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
label_count = sum(1 for _ in (CONVERTED / "labels").rglob("*.txt"))

assert samples_hash == EXPECTED_SAMPLES_SHA256, "samples.json không đúng phiên bản đã kiểm tra."
assert report["images"] == EXPECTED_IMAGES
assert report["instances"] == EXPECTED_INSTANCES
assert report["split_images"] == EXPECTED_SPLITS
assert len(manifest_rows) == EXPECTED_IMAGES
assert label_count == EXPECTED_IMAGES

print("Bronze source: PASS")
print("samples.json SHA-256: PASS")
print("Manifest rows:", len(manifest_rows))
print("Label files:", label_count)
print("Splits:", report["split_images"])
print("Source and conversion metadata: PASS")"""
        ),
        markdown(
            """## 5. Dựng dataset tạm có thể tiếp tục

Ảnh được copy vào `/content`, không chiếm dung lượng Drive mới. Thanh tiến độ cập nhật trực tiếp. Nếu runtime bị ngắt, chạy lại cell này để tiếp tục từ các file đã copy xong trong `.building`."""
        ),
        code(
            """import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
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

    if not source_image.is_file():
        raise FileNotFoundError(source_image)
    if not source_label.is_file():
        raise FileNotFoundError(source_label)

    reused_image, image_bytes = copy_if_needed(
        source_image,
        BUILDING_DATASET / "images" / split / image_name,
    )
    copy_if_needed(
        source_label,
        BUILDING_DATASET / "labels" / split / source_label.name,
    )
    return reused_image, image_bytes


def dataset_counts(root: Path) -> dict:
    return {
        split: {
            "images": len(list((root / "images" / split).glob("*.jpg"))),
            "labels": len(list((root / "labels" / split).glob("*.txt"))),
        }
        for split in EXPECTED_SPLITS
    }


if LOCAL_DATASET.exists():
    existing_counts = dataset_counts(LOCAL_DATASET)
    existing_splits = {split: values["images"] for split, values in existing_counts.items()}
    if existing_splits != EXPECTED_SPLITS or any(
        values["images"] != values["labels"] for values in existing_counts.values()
    ):
        raise RuntimeError(
            "Dataset /content đang tồn tại nhưng không đầy đủ. "
            "Hãy Restart runtime rồi chạy lại notebook."
        )
    print("Dataset tạm hoàn chỉnh đã tồn tại; sử dụng lại.")
else:
    BUILDING_DATASET.mkdir(parents=True, exist_ok=True)
    reused = 0
    copied_bytes = 0
    failures = []

    print("Bắt đầu/resume copy 2.816 ảnh. Có thể mất 10–30 phút.")
    print("Không dừng cell khi thanh tiến độ vẫn cập nhật.")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(stage_one, row): row for row in manifest_rows}
        with tqdm(total=len(futures), desc="Staging CarDD", unit="image") as progress:
            for future in as_completed(futures):
                row = futures[future]
                try:
                    was_reused, image_bytes = future.result()
                    reused += int(was_reused)
                    copied_bytes += image_bytes
                except Exception as error:
                    failures.append({"image": row.get("image"), "error": repr(error)})
                progress.update(1)
                if progress.n % 100 == 0:
                    progress.set_postfix(reused=reused, failures=len(failures))

    if failures:
        failure_report = NEW_PROJECT / "reports/cardd_staging_failures.json"
        failure_report.parent.mkdir(parents=True, exist_ok=True)
        failure_report.write_text(json.dumps(failures, indent=2), encoding="utf-8")
        raise RuntimeError(
            f"Có {len(failures)} file copy lỗi. Báo cáo: {failure_report}. "
            "Chạy lại cell để tự thử tiếp."
        )

    final_counts = dataset_counts(BUILDING_DATASET)
    actual_splits = {split: values["images"] for split, values in final_counts.items()}
    assert actual_splits == EXPECTED_SPLITS, (actual_splits, EXPECTED_SPLITS)
    assert all(values["images"] == values["labels"] for values in final_counts.values())

    data_yaml_payload = {
        "path": str(LOCAL_DATASET),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(report["classes"])},
    }
    (BUILDING_DATASET / "data.yaml").write_text(
        yaml.safe_dump(data_yaml_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    BUILDING_DATASET.replace(LOCAL_DATASET)
    print("Ảnh đã có sẵn và được dùng lại:", reused)
    print("Dung lượng ảnh kiểm tra (GB):", round(copied_bytes / 1024**3, 2))

DATA_YAML = LOCAL_DATASET / "data.yaml"
assert DATA_YAML.is_file()
print("Dataset staging: PASS")
print("Training YAML:", DATA_YAML)"""
        ),
        markdown("## 6. Validation trước huấn luyện"),
        code(
            """import json


def validate_yolo_dataset(root: Path) -> dict:
    summary = {"splits": {}, "errors": []}
    for split, expected in EXPECTED_SPLITS.items():
        images = sorted((root / "images" / split).glob("*.jpg"))
        labels = sorted((root / "labels" / split).glob("*.txt"))
        image_stems = {path.stem for path in images}
        label_stems = {path.stem for path in labels}
        invalid_rows = 0
        instances = 0
        for label in labels:
            for line in label.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) < 7 or (len(parts) - 1) % 2 != 0:
                    invalid_rows += 1
                    continue
                try:
                    class_id = int(parts[0])
                    coordinates = [float(value) for value in parts[1:]]
                except ValueError:
                    invalid_rows += 1
                    continue
                if class_id not in range(6) or any(value < 0 or value > 1 for value in coordinates):
                    invalid_rows += 1
                instances += 1
        split_result = {
            "images": len(images),
            "labels": len(labels),
            "instances": instances,
            "missing_labels": sorted(image_stems - label_stems),
            "orphan_labels": sorted(label_stems - image_stems),
            "invalid_rows": invalid_rows,
        }
        summary["splits"][split] = split_result
        if len(images) != expected or len(labels) != expected:
            summary["errors"].append(f"{split}: sai số lượng ảnh/nhãn")
        if split_result["missing_labels"] or split_result["orphan_labels"] or invalid_rows:
            summary["errors"].append(f"{split}: label không hợp lệ")

    summary["valid"] = not summary["errors"]
    return summary


validation = validate_yolo_dataset(LOCAL_DATASET)
assert validation["valid"], validation["errors"]
assert sum(item["instances"] for item in validation["splits"].values()) == EXPECTED_INSTANCES

REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
RUNS_ROOT.mkdir(parents=True, exist_ok=True)
validation_path = REPORTS_ROOT / "cardd_yolo_validation_before_training_v2.json"
validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(validation, ensure_ascii=False, indent=2))
print("Dataset validation: PASS")
print("Report:", validation_path)"""
        ),
        markdown(
            """## 7. Smoke test

Smoke test chạy 2 epoch trên 10% tập train. Nếu Colab ngắt sau khi đã có `last.pt`, chạy lại cell để resume."""
        ),
        code(
            """from datetime import datetime, timezone
import json
import shutil

from ultralytics import YOLO


def archive_unusable_run(run_dir: Path) -> None:
    if run_dir.exists():
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = run_dir.with_name(run_dir.name + "_incomplete_" + suffix)
        shutil.move(str(run_dir), str(archived))
        print("Đã lưu run chưa có checkpoint tại:", archived)


def train_or_resume(
    *,
    name: str,
    model_name: str,
    epochs: int,
    fraction: float,
    patience: int,
    save_period: int,
) -> Path:
    run_dir = RUNS_ROOT / name
    best = run_dir / "weights/best.pt"
    last = run_dir / "weights/last.pt"

    if best.is_file():
        print("Run đã có best.pt, sử dụng lại:", best)
        return best

    if last.is_file():
        print("Resume từ checkpoint:", last)
        YOLO(str(last)).train(resume=True)
    else:
        archive_unusable_run(run_dir)
        print("Bắt đầu run mới:", name)
        YOLO(model_name).train(
            data=str(DATA_YAML),
            project=str(RUNS_ROOT),
            name=name,
            epochs=epochs,
            imgsz=640,
            batch=8,
            patience=patience,
            workers=2,
            seed=SEED,
            deterministic=True,
            device=0,
            fraction=fraction,
            save_period=save_period,
            cache=False,
            amp=True,
            plots=True,
            exist_ok=False,
            verbose=True,
        )

    if not best.is_file():
        raise RuntimeError(f"Run {name} kết thúc nhưng không tạo best.pt")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "model": model_name,
        "data": str(DATA_YAML),
        "epochs": epochs,
        "fraction": fraction,
        "seed": SEED,
        "test_split_used": False,
        "best_checkpoint": str(best),
        "last_checkpoint": str(last),
    }
    (run_dir / "training_manifest_v2.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return best


SMOKE_BEST = train_or_resume(
    name="cardd_yolov8n_seg_smoke_v2",
    model_name="yolov8n-seg.pt",
    epochs=2,
    fraction=0.10,
    patience=2,
    save_period=1,
)

print("Smoke test: PASS")
print("Checkpoint:", SMOKE_BEST)"""
        ),
        markdown(
            """## 8. Baseline chính

YOLOv8n-seg chạy tối đa 100 epoch, early stopping patience 20 và lưu checkpoint mỗi 10 epoch. Checkpoint nằm trên Drive mới."""
        ),
        code(
            """if not RUN_BASELINE:
    print("Baseline đang tắt trong cấu hình.")
    BEST_WEIGHTS = None
else:
    BEST_WEIGHTS = train_or_resume(
        name="cardd_yolov8n_seg_baseline_v2",
        model_name="yolov8n-seg.pt",
        epochs=100,
        fraction=1.0,
        patience=20,
        save_period=10,
    )
    print("Baseline training: PASS")
    print("Best checkpoint:", BEST_WEIGHTS)"""
        ),
        markdown("## 9. Đánh giá trên validation"),
        code(
            """import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from ultralytics import YOLO
except ModuleNotFoundError:
    print("Runtime mới chưa có Ultralytics; đang cài bản 8.4.173...")
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
        ],
        check=True,
    )
    from ultralytics import YOLO

import torch
import yaml

if not torch.cuda.is_available():
    raise RuntimeError("Hãy chuyển runtime sang T4 GPU trước khi validation.")

# Cell này tự khôi phục toàn bộ đường dẫn sau khi Colab đổi runtime.
OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance")
SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
CONVERTED = NEW_PROJECT / "data/processed/cardd_yolo_v1"
RUNS_ROOT = NEW_PROJECT / "artifacts/image"
REPORTS_ROOT = NEW_PROJECT / "reports/metrics"
DATA_YAML = Path("/content/cardd_yolo_v1/data.yaml")

if not NEW_PROJECT.is_dir():
    from google.colab import drive

    drive.mount("/content/drive")

# Nếu dataset copy trong /content đã mất, tạo view symlink nhẹ để validation.
if not DATA_YAML.is_file():
    eval_dataset = Path("/content/cardd_yolo_eval_v2")
    manifest_path = CONVERTED / "split_manifest.jsonl"
    conversion_report_path = CONVERTED / "conversion_report.json"
    for required in [SOURCE_CARDD / "data", manifest_path, conversion_report_path]:
        if not required.exists():
            raise FileNotFoundError(required)

    manifest_rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    conversion_report = json.loads(conversion_report_path.read_text(encoding="utf-8"))
    if len(manifest_rows) != 2816:
        raise RuntimeError(f"Manifest không đủ 2.816 dòng: {len(manifest_rows)}")

    print("Dataset tạm đã mất; đang tạo validation view bằng symlink...")
    for index, row in enumerate(manifest_rows, start=1):
        image_name = row["image"]
        split = row["split"]
        source_image = SOURCE_CARDD / "data" / image_name
        source_label = CONVERTED / "labels" / split / f"{Path(image_name).stem}.txt"
        image_link = eval_dataset / "images" / split / image_name
        label_link = eval_dataset / "labels" / split / source_label.name
        image_link.parent.mkdir(parents=True, exist_ok=True)
        label_link.parent.mkdir(parents=True, exist_ok=True)
        for source, link in [(source_image, image_link), (source_label, label_link)]:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(source)
        if index % 500 == 0 or index == len(manifest_rows):
            print(f"Validation links: {index}/{len(manifest_rows)}")

    data_payload = {
        "path": str(eval_dataset),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            index: name
            for index, name in enumerate(conversion_report["classes"])
        },
    }
    DATA_YAML = eval_dataset / "data.yaml"
    DATA_YAML.write_text(
        yaml.safe_dump(data_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    val_images = len(list((eval_dataset / "images/val").glob("*.jpg")))
    val_labels = len(list((eval_dataset / "labels/val").glob("*.txt")))
    if (val_images, val_labels) != (431, 431):
        raise RuntimeError(
            f"Validation view không đủ: images={val_images}, labels={val_labels}"
        )
    print("Validation view: PASS")

print("Ultralytics ready: PASS")
print("CUDA:", torch.cuda.get_device_name(0))
print("Validation YAML:", DATA_YAML)

# Tự khôi phục đường dẫn checkpoint nếu runtime đã mất biến BEST_WEIGHTS.
runtime_best = globals().get("BEST_WEIGHTS")
default_best = (
    RUNS_ROOT
    / "cardd_yolov8n_seg_baseline_v2"
    / "weights"
    / "best.pt"
)
BEST_WEIGHTS = Path(runtime_best) if runtime_best is not None else default_best
if not BEST_WEIGHTS.is_file():
    BEST_WEIGHTS = None

REPORTS_ROOT.mkdir(parents=True, exist_ok=True)

if BEST_WEIGHTS is None:
    print("Chưa chạy baseline nên chưa đánh giá validation.")
    print("Không tìm thấy:", default_best)
else:
    print("Checkpoint:", BEST_WEIGHTS)
    VAL_METRICS = REPORTS_ROOT / "cardd_yolov8n_seg_val_v2.json"
    val_run_dir = RUNS_ROOT / "evaluation/cardd_yolov8n_seg_val_v2"

    if VAL_METRICS.is_file():
        val_report = json.loads(VAL_METRICS.read_text(encoding="utf-8"))
        print("Sử dụng validation report đã có:", VAL_METRICS)
    else:
        metrics = YOLO(str(BEST_WEIGHTS)).val(
            data=str(DATA_YAML),
            split="val",
            imgsz=640,
            batch=8,
            device=0,
            project=str(RUNS_ROOT / "evaluation"),
            name="cardd_yolov8n_seg_val_v2",
            plots=True,
            verbose=True,
            exist_ok=True,
        )
        val_report = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "weights": str(BEST_WEIGHTS),
            "split": "val",
            "test_split_used": False,
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
            "class_names": metrics.names,
            "run_directory": str(metrics.save_dir),
        }
        VAL_METRICS.write_text(
            json.dumps(val_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("Validation mask mAP50-95:", val_report["mask"]["map50_95"])
    print("Validation mask mAP50:", val_report["mask"]["map50"])
    print("Validation box mAP50-95:", val_report["box"]["map50_95"])
    print("Validation report:", VAL_METRICS)"""
        ),
        markdown(
            """## 10. Final test — khóa mặc định

Giữ `RUN_FINAL_TEST = False` trong giai đoạn lựa chọn model. Chỉ đổi thành `True` sau khi nhóm đã duyệt validation và khóa checkpoint. Cell từ chối chạy test lần hai nếu báo cáo đã tồn tại."""
        ),
        code(
            """RUN_FINAL_TEST = globals().get("RUN_FINAL_TEST", False)

if not RUN_FINAL_TEST:
    print("Final test vẫn đang khóa: PASS")
    print("Hãy gửi validation report cho nhóm trước khi mở test.")
else:
    if BEST_WEIGHTS is None:
        raise RuntimeError("Chưa có baseline checkpoint.")
    TEST_METRICS = REPORTS_ROOT / "cardd_yolov8n_seg_test_v2.json"
    if TEST_METRICS.exists():
        raise FileExistsError("Final test report đã tồn tại; không chạy test lần hai.")
    test_metrics = YOLO(str(BEST_WEIGHTS)).val(
        data=str(DATA_YAML),
        split="test",
        imgsz=640,
        batch=8,
        device=0,
        project=str(RUNS_ROOT / "evaluation"),
        name="cardd_yolov8n_seg_test_v2",
        plots=True,
        verbose=True,
        exist_ok=False,
    )
    test_report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "weights": str(BEST_WEIGHTS),
        "split": "test",
        "mask_map50_95": float(test_metrics.seg.map),
        "mask_map50": float(test_metrics.seg.map50),
        "box_map50_95": float(test_metrics.box.map),
        "run_directory": str(test_metrics.save_dir),
    }
    TEST_METRICS.write_text(
        json.dumps(test_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Final test completed exactly once:", TEST_METRICS)"""
        ),
        markdown(
            """## 11. Các nhánh tiếp theo

Sau CarDD, nhánh chứng từ sẽ tạo trường trích xuất và cờ kiểm tra nhất quán theo `claim_id`. Nhánh NetworkX sẽ tạo đặc trưng đồ thị từ các thực thể và quan hệ có thật trước thời điểm chấm điểm. Chỉ hợp nhất các nhánh khi có khóa `claim_id` hợp lệ; không ghép các dataset công khai không liên quan theo từng dòng."""
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
    build(Path("notebooks/CarDD_YOLOv8_Training_v2.ipynb"))
