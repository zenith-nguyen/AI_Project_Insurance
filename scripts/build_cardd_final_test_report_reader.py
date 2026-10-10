"""Build a read-only Colab notebook for an existing CarDD final-test report."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/CarDD_Final_Test_Report_Reader_Acc2_v1.ipynb")


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
            """# CarDD Final Test — đọc và xác minh report đã có

Notebook này **không chạy model**, không đọc lại test split và không cần GPU. Nó chỉ đọc report cùng execution lock đã được notebook final-test tạo ra, kiểm tra tính nhất quán và in kết quả để báo cáo."""
        ),
        markdown("## 1. Mount Drive và khai báo artifact đã khóa"),
        code(
            """import hashlib
import json
from pathlib import Path

from google.colab import drive

if not Path("/content/drive/MyDrive").is_dir():
    drive.mount("/content/drive")

NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
REPORTS_ROOT = NEW_PROJECT / "reports/metrics"
RUNS_ROOT = NEW_PROJECT / "artifacts/image"

FINAL_REPORT = REPORTS_ROOT / "cardd_yolov8s_seg_final_test_v1.json"
FINAL_LOCK = REPORTS_ROOT / "cardd_yolov8s_seg_final_test_v1.execution.json"
SELECTION_REPORT = REPORTS_ROOT / "cardd_yolo_model_selection_v1.json"
SELECTED_WEIGHTS = RUNS_ROOT / "cardd_yolov8s_seg_candidate_v1/weights/best.pt"

EXPECTED_CHECKPOINT_SHA256 = "6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b"
EXPECTED_TEST_IMAGES = 419
EXPECTED_TEST_INSTANCES = 931


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


required = [FINAL_REPORT, FINAL_LOCK, SELECTION_REPORT, SELECTED_WEIGHTS]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise FileNotFoundError("Thiếu artifact bắt buộc:\\n" + "\\n".join(missing))

print("Final report:", FINAL_REPORT)
print("Execution lock:", FINAL_LOCK)
print("Selection report:", SELECTION_REPORT)
print("Checkpoint:", SELECTED_WEIGHTS)"""
        ),
        markdown("## 2. Kiểm tra report, lock và checkpoint"),
        code(
            """final_report = json.loads(FINAL_REPORT.read_text(encoding="utf-8"))
execution = json.loads(FINAL_LOCK.read_text(encoding="utf-8"))
selection = json.loads(SELECTION_REPORT.read_text(encoding="utf-8"))

class_names_raw = final_report.get("class_names", {})
if isinstance(class_names_raw, dict):
    class_names = [
        name for _, name in sorted(class_names_raw.items(), key=lambda item: int(item[0]))
    ]
else:
    class_names = list(class_names_raw)

checks = {
    "split_is_test": final_report.get("split") == "test",
    "exactly_one_test_run": final_report.get("test_run_number") == 1,
    "expected_images": final_report.get("images") == EXPECTED_TEST_IMAGES,
    "expected_instances": final_report.get("instances") == EXPECTED_TEST_INSTANCES,
    "selected_model": final_report.get("model") == "yolov8s-seg candidate v1",
    "report_checkpoint_hash": final_report.get("weights_sha256") == EXPECTED_CHECKPOINT_SHA256,
    "selection_checkpoint_hash": selection.get("selected_checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA256,
    "checkpoint_hash_on_drive": sha256_file(SELECTED_WEIGHTS) == EXPECTED_CHECKPOINT_SHA256,
    "test_not_used_for_selection": selection.get("test_split_used") is False,
    "execution_completed": execution.get("status") == "completed",
    "same_run_id": execution.get("run_id") == final_report.get("run_id"),
    "lock_report_hash": execution.get("final_report_sha256") == sha256_file(FINAL_REPORT),
    "six_classes": len(class_names) == 6,
    "six_per_class_mask_metrics": len(final_report.get("mask", {}).get("per_class_map50_95", [])) == 6,
}

failed = [name for name, passed in checks.items() if not passed]
print(json.dumps(checks, ensure_ascii=False, indent=2))
if failed:
    raise RuntimeError("Final-test artifact không nhất quán: " + ", ".join(failed))

print("Final-test artifact verification: PASS")"""
        ),
        markdown("## 3. In kết quả final test để đưa vào báo cáo"),
        code(
            """mask = final_report["mask"]
box = final_report["box"]

print("\\n=== FINAL TEST REPORT RECOVERY: PASS ===")
print("Model:", final_report["model"])
print("Images:", final_report["images"])
print("Instances:", final_report["instances"])
print("Mask mAP50-95:", mask["map50_95"])
print("Mask mAP50:", mask["map50"])
print("Mask mAP75:", mask["map75"])
print("Box mAP50-95:", box["map50_95"])
print("Box mAP50:", box["map50"])
print("Box mAP75:", box["map75"])
print("\\nPer-class mask mAP50-95:")
for name, value in zip(class_names, mask["per_class_map50_95"]):
    print(f"- {name}: {float(value):.6f}")
print("\\nRun directory:", final_report.get("run_directory"))
print("Final report:", FINAL_REPORT)
print("Execution record:", FINAL_LOCK)
print("\\nKhông chạy lại final test: PASS")"""
        ),
        markdown(
            """## 4. Việc cần gửi lại

Gửi toàn bộ output bắt đầu từ `FINAL TEST REPORT RECOVERY: PASS`. Sau khi đọc các metric thật từ report, báo cáo CarDD có thể được đóng. Không xóa report hoặc execution lock và không chạy lại notebook final-test."""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "colab": {"name": OUTPUT.name, "provenance": []},
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
