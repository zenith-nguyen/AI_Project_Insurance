import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_SROIE_Processed_Split_Acc2_v1.ipynb")


def lines(text):
    return [line + "\n" for line in text.strip("\n").split("\n")]


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines(text),
    }


def main():
    cells = [
        markdown(
            """# SROIE Processed Split — Acc 2 v1

Notebook này xử lý leakage đã phát hiện trong mirror SROIE. Raw/Bronze không bị sửa. Quy tắc đã khóa: giữ nguyên 361 mẫu test, loại 8 bản train trùng tuyệt đối với test, rồi tạo validation 15% chỉ từ train sạch bằng seed cố định. Test không tham gia lựa chọn model."""
        ),
        markdown("## 1. Cấu hình và môi trường"),
        code(
            """from pathlib import Path

PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
REGISTRY_PATH = PROJECT / "data/registry/documents/document_sources_registry.json"
REMEDIATION_PATH = PROJECT / "data/registry/documents/remediation/sroie_source_split_dedup_v1.json"
OUTPUT_ROOT = PROJECT / "data/processed/documents/sroie/v1"
REPORT_PATH = PROJECT / "reports/data_audit/documents/sroie_processed_split_v1.json"

SEED = 20261011
VALIDATION_ROWS = 93
EXPECTED = {"source_train": 626, "removed": 8, "train": 525, "validation": 93, "test": 361}

print("Project:", PROJECT)
print("Output:", OUTPUT_ROOT)"""
        ),
        code(
            """import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "pyarrow>=15", "Pillow>=10"],
    check=True,
)

from google.colab import drive
drive.mount("/content/drive")

for required in (REGISTRY_PATH, REMEDIATION_PATH):
    if not required.is_file():
        raise FileNotFoundError(f"Thiếu artifact audit: {required}")
print("Environment: PASS")"""
        ),
        markdown("## 2. Đọc nguồn đã khóa và manifest remediation"),
        code(
            """import hashlib
import io
import json
import os
import shutil
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from PIL import Image


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
sources = {item["dataset_name"]: item for item in registry["sources"]}
sroie_root = Path(sources["sroie"]["inventory"]["path"])
remediation = json.loads(REMEDIATION_PATH.read_text(encoding="utf-8"))

remove_train_keys = set(remediation["remove_from_train_keys"])
preserve_test_keys = set(remediation["preserve_test_keys"])
if remediation["policy"] != "preserve_source_test_and_remove_exact_duplicates_from_train":
    raise RuntimeError("Remediation policy không đúng bản đã khóa.")
if len(remove_train_keys) != EXPECTED["removed"] or len(preserve_test_keys) != EXPECTED["removed"]:
    raise RuntimeError("Danh sách duplicate không đủ đúng 8 cặp.")

train_paths = sorted(path for path in sroie_root.rglob("*.parquet") if "train" in path.name.lower())
test_paths = sorted(path for path in sroie_root.rglob("*.parquet") if "test" in path.name.lower())
if not train_paths or not test_paths:
    raise FileNotFoundError("Không tìm thấy SROIE train/test parquet.")

train_raw = pa.concat_tables([pq.read_table(path) for path in train_paths])
test_table = pa.concat_tables([pq.read_table(path) for path in test_paths])
print("Raw rows:", {"train": train_raw.num_rows, "test": test_table.num_rows})
if train_raw.num_rows != EXPECTED["source_train"] or test_table.num_rows != EXPECTED["test"]:
    raise RuntimeError("SROIE source counts changed; dừng để audit lại.")"""
        ),
        markdown("## 3. Loại duplicate khỏi train và tạo validation cố định"),
        code(
            """train_keys = train_raw["key"].to_pylist()
test_keys = set(test_table["key"].to_pylist())
missing_remove_keys = sorted(remove_train_keys - set(train_keys))
missing_test_keys = sorted(preserve_test_keys - test_keys)
if missing_remove_keys or missing_test_keys:
    raise RuntimeError({"missing_train": missing_remove_keys, "missing_test": missing_test_keys})

keep_mask = pa.array([key not in remove_train_keys for key in train_keys])
clean_pool = train_raw.filter(keep_mask)
if clean_pool.num_rows != EXPECTED["train"] + EXPECTED["validation"]:
    raise RuntimeError("Số dòng train sạch không đúng 618.")

# Group identical images before splitting. The source train pool itself contains
# an exact duplicate pair; row-wise splitting can put its copies on two sides.
image_groups = {}
for index, value in enumerate(clean_pool["image"].to_pylist()):
    raw = value.get("bytes") if isinstance(value, dict) else value
    if raw is None:
        raise RuntimeError(f"Missing image bytes at clean-pool row {index}")
    digest = hashlib.sha256(raw).hexdigest()
    image_groups.setdefault(digest, []).append(index)

ranked_groups = sorted(
    image_groups.items(),
    key=lambda item: hashlib.sha256(f"{SEED}:{item[0]}".encode()).hexdigest(),
)

# Deterministic subset-sum chooses whole image groups while keeping exactly 93 rows.
choices = {0: []}
for digest, indices in ranked_groups:
    group_size = len(indices)
    for current_total in sorted(list(choices), reverse=True):
        new_total = current_total + group_size
        if new_total <= VALIDATION_ROWS and new_total not in choices:
            choices[new_total] = choices[current_total] + [(digest, indices)]
    if VALIDATION_ROWS in choices:
        break
if VALIDATION_ROWS not in choices:
    raise RuntimeError("Không thể tạo validation 93 dòng mà vẫn giữ nguyên duplicate groups.")

validation_indices = sorted(
    index for _, indices in choices[VALIDATION_ROWS] for index in indices
)
validation_set = set(validation_indices)
train_indices = [index for index in range(clean_pool.num_rows) if index not in validation_set]

train_table = clean_pool.take(pa.array(train_indices, type=pa.int64()))
validation_table = clean_pool.take(pa.array(validation_indices, type=pa.int64()))

observed = {
    "train": train_table.num_rows,
    "validation": validation_table.num_rows,
    "test": test_table.num_rows,
}
print("Processed rows:", observed)
print("Unique image groups in clean pool:", len(image_groups))
print("Internal duplicate groups kept intact:", sum(len(rows) > 1 for rows in image_groups.values()))
if observed != {name: EXPECTED[name] for name in ("train", "validation", "test")}:
    raise RuntimeError("Processed split counts failed.")"""
        ),
        markdown("## 4. Ghi Processed và xác minh không leakage"),
        code(
            """LOCAL_BUILD = Path("/content/sroie_processed_v1_build")
if LOCAL_BUILD.exists():
    shutil.rmtree(LOCAL_BUILD)
LOCAL_BUILD.mkdir(parents=True)

tables = {"train": train_table, "validation": validation_table, "test": test_table}
for split, table in tables.items():
    pq.write_table(table, LOCAL_BUILD / f"{split}.parquet", compression="zstd")


def image_hashes(table):
    hashes = set()
    corrupt = []
    for row_index, value in enumerate(table["image"].to_pylist()):
        raw = value.get("bytes") if isinstance(value, dict) else value
        try:
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            hashes.add(hashlib.sha256(raw).hexdigest())
        except Exception as error:
            corrupt.append({"row": row_index, "error": repr(error)})
    return hashes, corrupt


hashes = {}
corrupt = {}
for split, table in tables.items():
    hashes[split], corrupt[split] = image_hashes(table)

overlaps = {
    "train__validation": len(hashes["train"] & hashes["validation"]),
    "train__test": len(hashes["train"] & hashes["test"]),
    "validation__test": len(hashes["validation"] & hashes["test"]),
}
print("Cross-split exact duplicates:", overlaps)
if any(corrupt.values()) or any(overlaps.values()):
    raise RuntimeError({"corrupt": corrupt, "overlaps": overlaps})

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
file_records = {}
for split in tables:
    source = LOCAL_BUILD / f"{split}.parquet"
    target = OUTPUT_ROOT / source.name
    temporary = target.with_suffix(".parquet.tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    file_records[split] = {
        "path": str(target),
        "rows": tables[split].num_rows,
        "sha256": sha256_file(target),
        "bytes": target.stat().st_size,
    }

report = {
    "schema_version": 1,
    "created_at": utc_now(),
    "source": "sroie",
    "source_inventory": str(sroie_root),
    "remediation_manifest": str(REMEDIATION_PATH),
    "policy": remediation["policy"],
    "split_policy": "deterministic_group_by_image_sha256_subset_sum",
    "seed": SEED,
    "clean_pool_unique_image_groups": len(image_groups),
    "clean_pool_internal_duplicate_groups": sum(
        len(rows) > 1 for rows in image_groups.values()
    ),
    "removed_train_keys": sorted(remove_train_keys),
    "test_used_for_split_or_selection": False,
    "files": file_records,
    "cross_split_exact_duplicates": overlaps,
    "valid": True,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
temporary_report = REPORT_PATH.with_suffix(".json.tmp")
temporary_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(temporary_report, REPORT_PATH)

print("\\n=== SROIE PROCESSED SPLIT: PASS ===")
print("Rows:", observed)
print("Removed train duplicates:", len(remove_train_keys))
print("Test used for selection:", report["test_used_for_split_or_selection"])
print("Processed root:", OUTPUT_ROOT)
print("Report:", REPORT_PATH)"""
        ),
        markdown(
            """## 5. Sau khi PASS

Gửi toàn bộ output cuối. Bước kế tiếp là benchmark ba phần riêng: phân loại loại chứng từ, OCR và trích xuất trường. Chưa chạy test để chọn model; chỉ dùng train/validation. Public data phục vụ benchmark nghiên cứu, chưa đủ để phát hành sản phẩm bảo hiểm thương mại."""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "colab": {"name": OUTPUT.name, "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
