"""Build the UTF-8-safe Colab notebook used to resume CarDD on a new Drive."""
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
            """# Tiếp tục dự án trên Google Drive mới

Notebook này dùng Bronze từ shortcut Drive cũ và ghi kết quả mới vào Drive mới. Notebook không chạy lại nhánh tabular, không chứa token và không copy ảnh CarDD vào Processed.

Trước khi chạy:
1. Mở notebook bằng tài khoản Google mới.
2. Share project từ Drive cũ và thêm shortcut vào My Drive mới với tên `AI_Project_Insurance_OLD`.
3. Chuẩn bị file ZIP code/report do Codex tạo."""
        ),
        code(
            """from google.colab import drive
drive.mount("/content/drive")"""
        ),
        code(
            """from pathlib import Path

OLD_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_OLD")
NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance")

print("Đọc dữ liệu cũ từ:", OLD_PROJECT)
print("Ghi kết quả mới vào:", NEW_PROJECT)

if not OLD_PROJECT.exists():
    raise FileNotFoundError(
        "Không thấy shortcut Drive cũ. Hãy sửa OLD_PROJECT theo tên shortcut trong MyDrive."
    )"""
        ),
        markdown(
            """## Upload gói code mới

Chọn file `AI_Project_Insurance_code_reports_2026-10-07.zip`. File này không chứa raw data hoặc model artifact."""
        ),
        code(
            """from google.colab import files
import zipfile

uploaded = files.upload()
zip_files = [name for name in uploaded if name.lower().endswith(".zip")]
if len(zip_files) != 1:
    raise RuntimeError("Hãy upload đúng một file ZIP code/report.")

bundle = Path("/content") / zip_files[0]
bundle.write_bytes(uploaded[zip_files[0]])
NEW_PROJECT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(bundle) as archive:
    archive.extractall(NEW_PROJECT)

print("Đã giải nén code vào:", NEW_PROJECT)"""
        ),
        markdown(
            """## Kiểm tra Drive cũ

Nếu Bronze đầy đủ nhưng conversion metadata bị thiếu, notebook sẽ tạo lại labels và split trên Drive mới. Đây là trường hợp dự kiến khi Drive cũ đã đầy."""
        ),
        code(
            """import json
import subprocess
import sys

checker = NEW_PROJECT / "scripts/check_cardd_resume_state.py"
completed = subprocess.run(
    ["python", str(checker), str(OLD_PROJECT)],
    check=True,
    capture_output=True,
    text=True,
)
old_state = json.loads(completed.stdout)
print(json.dumps(old_state, ensure_ascii=False, indent=2))

if not old_state["bronze"]["ready"]:
    raise RuntimeError("Bronze chưa hoàn chỉnh; dừng trước khi ghi dữ liệu mới.")

EXPECTED_V2 = {"train": 1966, "val": 431, "test": 419}
old_has_v2 = (
    old_state["conversion"]["metadata_ready"]
    and old_state["conversion"]["reported_split_images"] == EXPECTED_V2
)
print("Drive cũ có conversion v2 dùng lại được:", old_has_v2)"""
        ),
        markdown(
            """## Chuẩn bị conversion v2 trên Drive mới

- Nếu Drive cũ còn conversion v2, cell copy labels/manifest/report nhỏ.
- Nếu metadata bị thiếu, cell chạy lại converter với `labels-only`; 2.816 ảnh vẫn chỉ nằm trong Bronze cũ."""
        ),
        code(
            """import shutil

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "ultralytics>=8,<9",
        "iterative-stratification==0.1.9",
        "PyYAML>=6",
        "Pillow>=10",
    ],
    check=True,
)

SOURCE_CARDD = OLD_PROJECT / "data/bronze/layerA_cardd"
NEW_PROCESSED = NEW_PROJECT / "data/processed/cardd_yolo_v1"

if old_has_v2:
    old_processed = OLD_PROJECT / "data/processed/cardd_yolo_v1"
    NEW_PROCESSED.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        old_processed / "labels",
        NEW_PROCESSED / "labels",
        dirs_exist_ok=True,
    )
    for filename in ["conversion_report.json", "split_manifest.jsonl"]:
        shutil.copy2(old_processed / filename, NEW_PROCESSED / filename)
    print("Đã dùng lại labels và metadata v2 từ Drive cũ.")
elif not NEW_PROCESSED.exists():
    converter = NEW_PROJECT / "scripts/convert_cardd_fiftyone_to_yolo.py"
    subprocess.run(
        [
            sys.executable,
            str(converter),
            str(SOURCE_CARDD),
            str(NEW_PROCESSED),
            "--seed",
            "20261006",
            "--image-mode",
            "labels-only",
            "--near-duplicate-hamming",
            "2",
        ],
        check=True,
    )
    print("Đã tạo lại conversion v2 dạng labels-only trên Drive mới.")
else:
    print("Output mới đã tồn tại; sẽ kiểm tra trước khi quyết định chạy lại.")"""
        ),
        markdown("""## Xác minh source cũ và conversion mới"""),
        code(
            """completed = subprocess.run(
    [
        sys.executable,
        str(checker),
        str(OLD_PROJECT),
        "--conversion-project",
        str(NEW_PROJECT),
    ],
    check=True,
    capture_output=True,
    text=True,
)
state = json.loads(completed.stdout)
print(json.dumps(state, ensure_ascii=False, indent=2))

if not state["resume"]["ready_to_materialize"]:
    raise RuntimeError("Conversion mới chưa đồng bộ với Bronze.")
if state["conversion"]["reported_split_images"] != EXPECTED_V2:
    raise RuntimeError("Split mới không khớp conversion v2 dự kiến.")

print("Kiểm tra resume: PASS")"""
        ),
        markdown(
            """## Dựng dataset tạm và validate

Dataset tạm nằm trong `/content`, nên không làm tăng dung lượng Drive mới."""
        ),
        code(
            """TEMP_DATASET = Path("/content/cardd_yolo_v1")
if TEMP_DATASET.exists():
    shutil.rmtree(TEMP_DATASET)

subprocess.run(
    [
        sys.executable,
        str(NEW_PROJECT / "scripts/materialize_cardd_training_view.py"),
        str(SOURCE_CARDD),
        str(NEW_PROCESSED),
        str(TEMP_DATASET),
    ],
    check=True,
)

validation_path = Path("/content/cardd_yolo_validation_v2.json")
subprocess.run(
    [
        sys.executable,
        str(NEW_PROJECT / "scripts/validate_yolo_seg_dataset.py"),
        str(TEMP_DATASET),
        "--output",
        str(validation_path),
    ],
    check=True,
)

validation = json.loads(validation_path.read_text(encoding="utf-8"))
print("Dataset hợp lệ:", validation["valid"])
print("File dùng để train:", TEMP_DATASET / "data.yaml")

reports = NEW_PROJECT / "reports"
reports.mkdir(parents=True, exist_ok=True)
shutil.copy2(validation_path, reports / validation_path.name)"""
        ),
        markdown(
            """## Điểm dừng

Nếu cell cuối in `Dataset hợp lệ: True`, phần dữ liệu đã sẵn sàng. Chưa chạy training trong notebook này. Trước khi train CarDD, lưu bằng chứng prior consent của PIC Lab."""
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
    build(Path("notebooks/AI_Project_Insurance_Resume_New_Drive_v2.ipynb"))
