"""Build the UTF-8-safe Colab notebook for the CarDD YOLOv8 baseline."""
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
            """# Huấn luyện CarDD YOLOv8-seg — baseline v1

Protocol: smoke test → baseline trên train → chọn `best.pt` bằng validation → test chỉ chạy sau khi model được khóa.

Trước khi chạy, chọn **Runtime → Change runtime type → T4 GPU**. Notebook đọc Bronze qua shortcut Drive cũ, nhưng copy ảnh vào `/content` để train nhanh hơn. Ảnh tạm sẽ mất khi runtime kết thúc và không chiếm dung lượng Drive."""
        ),
        code(
            """import subprocess
import sys
import torch

print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise RuntimeError("Hãy đổi Colab runtime sang T4 GPU rồi chạy lại từ đầu.")

print("GPU:", torch.cuda.get_device_name(0))
print("GPU memory GB:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))"""
        ),
        code(
            """from google.colab import drive
drive.mount("/content/drive")"""
        ),
        code(
            """from pathlib import Path

OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance")
SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
CONVERTED = NEW_PROJECT / "data/processed/cardd_yolo_v1"
LOCAL_DATASET = Path("/content/cardd_yolo_v1")
RUNS_ROOT = NEW_PROJECT / "artifacts/image"
REPORTS = NEW_PROJECT / "reports/metrics"

for required in [SOURCE_CARDD, CONVERTED / "conversion_report.json"]:
    if not required.exists():
        raise FileNotFoundError(required)

print("Bronze source:", SOURCE_CARDD)
print("Persistent labels:", CONVERTED)
print("Ephemeral training data:", LOCAL_DATASET)
print("Persistent runs:", RUNS_ROOT)"""
        ),
        markdown(
            """## Cập nhật code

Upload `AI_Project_Insurance_training_bundle_2026-10-07.zip`. Gói này không chứa raw images hoặc model weights."""
        ),
        code(
            """from google.colab import files
import zipfile

uploaded = files.upload()
zip_names = [name for name in uploaded if name.lower().endswith(".zip")]
if len(zip_names) != 1:
    raise RuntimeError("Hãy upload đúng một training bundle ZIP.")

bundle_path = Path("/content") / zip_names[0]
bundle_path.write_bytes(uploaded[zip_names[0]])
with zipfile.ZipFile(bundle_path) as archive:
    archive.extractall(NEW_PROJECT)

print("Đã cập nhật code tại:", NEW_PROJECT)"""
        ),
        code(
            """subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "ultralytics==8.4.173",
        "iterative-stratification==0.1.9",
        "PyYAML>=6,<7",
        "Pillow>=10,<13",
    ],
    check=True,
)

import importlib.metadata as metadata
print("Ultralytics:", metadata.version("ultralytics"))"""
        ),
        markdown(
            """## Stage dữ liệu vào disk tạm

Cell copy 2.816 ảnh vào `/content`; không ghi thêm ảnh vào Drive."""
        ),
        code(
            """import shutil

if LOCAL_DATASET.exists():
    shutil.rmtree(LOCAL_DATASET)

subprocess.run(
    [
        sys.executable,
        str(NEW_PROJECT / "scripts/materialize_cardd_training_view.py"),
        str(SOURCE_CARDD),
        str(CONVERTED),
        str(LOCAL_DATASET),
        "--image-mode",
        "copy",
    ],
    check=True,
)

DATA_YAML = LOCAL_DATASET / "data.yaml"
print("Training YAML:", DATA_YAML)"""
        ),
        code(
            """REPORTS.mkdir(parents=True, exist_ok=True)
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

subprocess.run(
    [
        sys.executable,
        str(NEW_PROJECT / "scripts/validate_yolo_seg_dataset.py"),
        str(LOCAL_DATASET),
        "--output",
        str(REPORTS / "cardd_yolo_validation_before_training.json"),
    ],
    check=True,
)

preflight = subprocess.run(
    [
        sys.executable,
        str(NEW_PROJECT / "scripts/preflight_cardd_training.py"),
        "--data",
        str(DATA_YAML),
        "--output-root",
        str(RUNS_ROOT),
    ],
    check=True,
    capture_output=True,
    text=True,
)
print(preflight.stdout)"""
        ),
        markdown(
            """## Smoke test

Hai epoch trên 10% train để kiểm tra CUDA, loss, checkpoint và toàn bộ pipeline. Test split không được dùng."""
        ),
        code(
            """SMOKE_NAME = "cardd_yolov8n_seg_smoke_v1"
SMOKE_DIR = RUNS_ROOT / SMOKE_NAME
SMOKE_BEST = SMOKE_DIR / "weights/best.pt"

if SMOKE_BEST.is_file():
    print("Smoke test đã tồn tại, dùng lại:", SMOKE_BEST)
elif SMOKE_DIR.exists():
    raise RuntimeError("Smoke run tồn tại nhưng chưa hoàn tất. Gửi trạng thái thư mục cho Codex.")
else:
    subprocess.run(
        [
            sys.executable,
            str(NEW_PROJECT / "src/image/train_yolo.py"),
            "--data", str(DATA_YAML),
            "--project", str(RUNS_ROOT),
            "--name", SMOKE_NAME,
            "--model", "yolov8n-seg.pt",
            "--epochs", "2",
            "--imgsz", "640",
            "--batch", "8",
            "--patience", "2",
            "--workers", "2",
            "--seed", "20261007",
            "--device", "0",
            "--fraction", "0.10",
            "--save-period", "1",
        ],
        check=True,
    )

if not SMOKE_BEST.is_file():
    raise RuntimeError("Smoke test không tạo best.pt.")
print("Smoke test: PASS", SMOKE_BEST)"""
        ),
        markdown(
            """## Baseline chính

Tối đa 100 epoch, patience 20 và checkpoint mỗi 10 epoch. Output được lưu trực tiếp trên Drive mới để có thể resume sau khi Colab ngắt."""
        ),
        code(
            """BASELINE_NAME = "cardd_yolov8n_seg_baseline_v1"
BASELINE_DIR = RUNS_ROOT / BASELINE_NAME
BEST_WEIGHTS = BASELINE_DIR / "weights/best.pt"
LAST_WEIGHTS = BASELINE_DIR / "weights/last.pt"
TRAIN_MANIFEST = BASELINE_DIR / "training_manifest.json"

if BEST_WEIGHTS.is_file() and TRAIN_MANIFEST.is_file():
    print("Baseline đã hoàn tất, dùng lại:", BEST_WEIGHTS)
elif LAST_WEIGHTS.is_file():
    print("Resume baseline từ:", LAST_WEIGHTS)
    subprocess.run(
        [
            sys.executable,
            str(NEW_PROJECT / "src/image/train_yolo.py"),
            "--data", str(DATA_YAML),
            "--project", str(RUNS_ROOT),
            "--resume-checkpoint", str(LAST_WEIGHTS),
        ],
        check=True,
    )
else:
    subprocess.run(
        [
            sys.executable,
            str(NEW_PROJECT / "src/image/train_yolo.py"),
            "--data", str(DATA_YAML),
            "--project", str(RUNS_ROOT),
            "--name", BASELINE_NAME,
            "--model", "yolov8n-seg.pt",
            "--epochs", "100",
            "--imgsz", "640",
            "--batch", "8",
            "--patience", "20",
            "--workers", "2",
            "--seed", "20261007",
            "--device", "0",
            "--fraction", "1.0",
            "--save-period", "10",
        ],
        check=True,
    )

if not BEST_WEIGHTS.is_file():
    raise RuntimeError("Baseline chưa tạo best.pt.")
print("Best checkpoint:", BEST_WEIGHTS)"""
        ),
        markdown("""## Đánh giá trên validation"""),
        code(
            """VAL_METRICS = REPORTS / "cardd_yolov8n_seg_val_v1.json"

if VAL_METRICS.is_file():
    print("Validation report đã tồn tại:", VAL_METRICS)
else:
    subprocess.run(
        [
            sys.executable,
            str(NEW_PROJECT / "src/image/evaluate_yolo.py"),
            "--weights", str(BEST_WEIGHTS),
            "--data", str(DATA_YAML),
            "--output", str(VAL_METRICS),
            "--split", "val",
            "--project", str(RUNS_ROOT / "evaluation"),
            "--name", "cardd_yolov8n_seg_val_v1",
            "--imgsz", "640",
            "--batch", "8",
            "--device", "0",
        ],
        check=True,
    )

import json
val_report = json.loads(VAL_METRICS.read_text(encoding="utf-8"))
print("Validation mask mAP50-95:", val_report["mask"]["map50_95"])
print("Validation mask mAP50:", val_report["mask"]["map50"])
print("Validation box mAP50-95:", val_report["box"]["map50_95"])
print("Per-class mask mAP50-95:", val_report["mask"]["per_class_map50_95"])"""
        ),
        markdown(
            """## Final test — khóa mặc định

Giữ `RUN_FINAL_TEST = False` cho đến khi nhóm đã xem validation, quyết định có thử YOLOv8s hay không và khóa checkpoint. Khi đó đổi thành `True` để test đúng một lần."""
        ),
        code(
            """RUN_FINAL_TEST = False

if not RUN_FINAL_TEST:
    print("Test vẫn được khóa. Hãy gửi validation report cho Codex trước.")
else:
    TEST_METRICS = REPORTS / "cardd_yolov8n_seg_test_v1.json"
    if TEST_METRICS.exists():
        raise FileExistsError("Final test report đã tồn tại; không chạy test lần hai.")
    subprocess.run(
        [
            sys.executable,
            str(NEW_PROJECT / "src/image/evaluate_yolo.py"),
            "--weights", str(BEST_WEIGHTS),
            "--data", str(DATA_YAML),
            "--output", str(TEST_METRICS),
            "--split", "test",
            "--allow-test",
            "--project", str(RUNS_ROOT / "evaluation"),
            "--name", "cardd_yolov8n_seg_test_v1",
            "--imgsz", "640",
            "--batch", "8",
            "--device", "0",
        ],
        check=True,
    )"""
        ),
        markdown(
            """## Bước sau CarDD

Nhánh chứng từ sẽ tạo extracted fields và consistency flags theo `claim_id`. NetworkX sẽ tạo graph features từ entity thật và chỉ dùng edge có trước scoring time. Các module chỉ được ghép ở claim-level khi có khóa liên kết hợp lệ; không nối các dataset công khai không liên quan theo dòng."""
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
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
    build(Path("notebooks/CarDD_YOLOv8_Training_v1.ipynb"))
