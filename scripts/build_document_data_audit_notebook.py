import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_Data_Audit_Acc2_v1.ipynb")


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
            """# Document Data Audit — Acc 2 v1

Notebook này đọc trực tiếp Bronze và registry do `Document_Data_Intake_Acc2_v1.ipynb` tạo. Nó không train model và không thay đổi dữ liệu gốc. Kết quả gồm kiểm tra manifest, số mẫu, archive/file hỏng, checksum, cân bằng RVL sample và exact-duplicate leakage giữa các split.

Kết quả tự động không thay thế việc review PII/license thủ công. Research baseline và production release là hai cổng riêng."""
        ),
        markdown("## 1. Cấu hình"),
        code(
            """from pathlib import Path

NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
BRONZE_ROOT = NEW_PROJECT / "data/bronze/documents"
REGISTRY_ROOT = NEW_PROJECT / "data/registry/documents"
AUDIT_ROOT = NEW_PROJECT / "reports/data_audit/documents"

REGISTRY_PATH = REGISTRY_ROOT / "document_sources_registry.json"
AUDIT_JSON = AUDIT_ROOT / "document_data_audit_v1.json"
AUDIT_MD = AUDIT_ROOT / "DOCUMENT_DATA_AUDIT_V1.md"

EXPECTED = {
    "cord_v2": {"rows": 1000, "splits": {"train": 800, "validation": 100, "test": 100}},
    "funsd": {"rows": 199},
    "sroie": {"rows": 973, "splits": {"train": 626, "test": 347}},
    "rvl_cdip": {"sample_rows": 1600, "classes": 16, "per_class": 100},
    "xfund": {"languages": 7, "assets": 28},
}

print("Project:", NEW_PROJECT)
print("Registry:", REGISTRY_PATH)"""
        ),
        markdown("## 2. Môi trường"),
        code(
            """import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "Pillow>=10", "pyarrow>=15"],
    check=True,
)

from google.colab import drive
drive.mount("/content/drive")

if not REGISTRY_PATH.is_file():
    raise FileNotFoundError("Thiếu document_sources_registry.json; chạy intake trước.")

AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
print("Environment: PASS")"""
        ),
        markdown("## 3. Hàm audit dùng chung"),
        code(
            """import hashlib
import io
import json
import os
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

import pyarrow.parquet as pq
from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


def sha256_file(path: Path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_physical_images(paths):
    corrupt = []
    hashes = {}
    for path in paths:
        try:
            with Image.open(path) as image:
                image.verify()
            hashes[str(path)] = sha256_file(path)
        except Exception as error:
            corrupt.append({"path": str(path), "error": repr(error)})
    return hashes, corrupt


def split_from_name(name: str):
    lowered = name.lower()
    if "validation" in lowered or ".val" in lowered or "_val" in lowered:
        return "validation"
    if "test" in lowered:
        return "test"
    if "train" in lowered:
        return "train"
    return "unknown"


def parquet_image_audit(paths):
    split_rows = Counter()
    split_hashes = defaultdict(set)
    corrupt = []
    schemas = {}
    for path in paths:
        split = split_from_name(path.name)
        parquet = pq.ParquetFile(path)
        split_rows[split] += parquet.metadata.num_rows
        schemas[str(path)] = parquet.schema_arrow.names
        if "image" not in parquet.schema_arrow.names:
            continue
        for batch in parquet.iter_batches(columns=["image"], batch_size=32):
            for scalar in batch.column(0):
                value = scalar.as_py()
                raw = value.get("bytes") if isinstance(value, dict) else value
                if raw is None:
                    corrupt.append({"path": str(path), "error": "image bytes missing"})
                    continue
                try:
                    with Image.open(io.BytesIO(raw)) as image:
                        image.verify()
                    split_hashes[split].add(hashlib.sha256(raw).hexdigest())
                except Exception as error:
                    corrupt.append({"path": str(path), "error": repr(error)})
    overlaps = {}
    names = sorted(split_hashes)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            overlaps[f"{left}__{right}"] = len(split_hashes[left] & split_hashes[right])
    return {
        "split_rows": dict(split_rows),
        "unique_image_hashes": {key: len(value) for key, value in split_hashes.items()},
        "cross_split_exact_duplicates": overlaps,
        "corrupt_images": corrupt,
        "schemas": schemas,
    }


def audit_zip(path: Path, include_image_hashes=False):
    image_hashes = set()
    unsafe = []
    corrupt_member = None
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                unsafe.append(member.filename)
            if include_image_hashes and member_path.suffix.lower() in IMAGE_EXTENSIONS:
                raw = archive.read(member)
                image_hashes.add(hashlib.sha256(raw).hexdigest())
        corrupt_member = archive.testzip()
    return {
        "unsafe_members": unsafe,
        "corrupt_member": corrupt_member,
        "image_hashes": image_hashes,
    }


def no_overlap(overlaps):
    return all(value == 0 for value in overlaps.values())"""
        ),
        markdown("## 4. Registry và manifest"),
        code(
            """registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
sources = {item["dataset_name"]: item for item in registry.get("sources", [])}
required_sources = {"cord_v2", "funsd", "xfund", "sroie", "rvl_cdip", "midv500", "midv2020"}
missing_sources = sorted(required_sources - set(sources))
manifest_errors = []
for name, item in sources.items():
    inventory_path = Path(item["inventory"]["path"])
    manifest_path = inventory_path / "source_manifest.json"
    if not inventory_path.is_dir() or not manifest_path.is_file():
        manifest_errors.append(name)

print("Sources:", sorted(sources))
print("Missing sources:", missing_sources)
print("Manifest errors:", manifest_errors)
if missing_sources or manifest_errors:
    raise RuntimeError("Registry/manifest preflight failed.")
print("Registry and manifests: PASS")"""
        ),
        markdown("## 5. CORD và SROIE parquet"),
        code(
            """parquet_results = {}
for source_name in ["cord_v2", "sroie"]:
    source_root = Path(sources[source_name]["inventory"]["path"])
    parquet_paths = sorted(source_root.rglob("*.parquet"))
    if not parquet_paths:
        raise RuntimeError(f"{source_name}: không tìm thấy parquet")
    result = parquet_image_audit(parquet_paths)
    expected = EXPECTED[source_name]
    observed_total = sum(result["split_rows"].values())
    result["expected_total"] = expected["rows"]
    result["row_count_pass"] = observed_total == expected["rows"]
    result["split_count_pass"] = result["split_rows"] == expected["splits"]
    result["image_decode_pass"] = not result["corrupt_images"]
    result["leakage_pass"] = no_overlap(result["cross_split_exact_duplicates"])
    parquet_results[source_name] = result
    print(source_name, result["split_rows"])
    print("  decode:", result["image_decode_pass"], "leakage:", result["leakage_pass"])

if not all(
    item["row_count_pass"] and item["split_count_pass"]
    and item["image_decode_pass"] and item["leakage_pass"]
    for item in parquet_results.values()
):
    raise RuntimeError("CORD/SROIE parquet audit failed.")
print("CORD and SROIE: PASS")"""
        ),
        markdown("## 6. FUNSD"),
        code(
            """funsd_root = Path(sources["funsd"]["inventory"]["path"])
funsd_images = sorted(
    path for path in funsd_root.rglob("*")
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
)
funsd_hashes, funsd_corrupt = verify_physical_images(funsd_images)
funsd_json = sorted(path for path in funsd_root.rglob("*.json") if path.name != "source_manifest.json")
funsd_duplicate_hashes = {
    digest: count for digest, count in Counter(funsd_hashes.values()).items() if count > 1
}
funsd_result = {
    "images": len(funsd_images),
    "annotations": len(funsd_json),
    "corrupt_images": funsd_corrupt,
    "exact_duplicate_hashes": funsd_duplicate_hashes,
    "count_pass": len(funsd_images) == EXPECTED["funsd"]["rows"],
    "pairing_pass": len(funsd_images) == len(funsd_json),
}
print(funsd_result)
if not funsd_result["count_pass"] or not funsd_result["pairing_pass"] or funsd_corrupt:
    raise RuntimeError("FUNSD audit failed.")
print("FUNSD: PASS")"""
        ),
        markdown("## 7. XFUND archives và checksum"),
        code(
            """xfund_root = Path(sources["xfund"]["inventory"]["path"])
xfund_manifest = json.loads((xfund_root / "source_manifest.json").read_text(encoding="utf-8"))
asset_by_name = {item["name"]: item for item in xfund_manifest.get("assets", [])}
asset_paths = sorted((xfund_root / "raw/release_assets").glob("*"))
checksum_errors = []
zip_errors = []
xfund_split_hashes = defaultdict(set)
for path in asset_paths:
    expected_sha = asset_by_name.get(path.name, {}).get("sha256")
    if expected_sha and sha256_file(path) != expected_sha:
        checksum_errors.append(path.name)
    if path.suffix.lower() == ".zip":
        result = audit_zip(path, include_image_hashes=True)
        if result["unsafe_members"] or result["corrupt_member"]:
            zip_errors.append({"name": path.name, **result, "image_hashes": None})
        xfund_split_hashes[split_from_name(path.name)] |= result["image_hashes"]

xfund_overlap = {
    "train__validation": len(
        xfund_split_hashes.get("train", set())
        & xfund_split_hashes.get("validation", set())
    )
}
xfund_result = {
    "assets": len(asset_paths),
    "checksum_errors": checksum_errors,
    "zip_errors": zip_errors,
    "unique_images_by_split": {key: len(value) for key, value in xfund_split_hashes.items()},
    "cross_split_exact_duplicates": xfund_overlap,
    "asset_count_pass": len(asset_paths) == EXPECTED["xfund"]["assets"],
    "leakage_pass": no_overlap(xfund_overlap),
}
print(xfund_result)
if not xfund_result["asset_count_pass"] or checksum_errors or zip_errors or not xfund_result["leakage_pass"]:
    raise RuntimeError("XFUND audit failed.")
print("XFUND: PASS")"""
        ),
        markdown("## 8. RVL-CDIP balanced sample"),
        code(
            """rvl_root = Path(sources["rvl_cdip"]["inventory"]["path"])
rvl_manifest_path = rvl_root / "sample_manifest.jsonl"
if not rvl_manifest_path.is_file():
    raise FileNotFoundError("Thiếu RVL sample_manifest.jsonl")
rvl_rows = [
    json.loads(line) for line in rvl_manifest_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
rvl_counts = Counter(row["class_name"] for row in rvl_rows)
rvl_missing = []
rvl_hash_errors = []
rvl_corrupt = []
for row in rvl_rows:
    path = rvl_root / row["relative_path"]
    if not path.is_file():
        rvl_missing.append(str(path))
        continue
    actual = sha256_file(path)
    if actual != row["sha256"]:
        rvl_hash_errors.append(str(path))
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as error:
        rvl_corrupt.append({"path": str(path), "error": repr(error)})

rvl_duplicate_hashes = {
    digest: count for digest, count in Counter(row["sha256"] for row in rvl_rows).items()
    if count > 1
}
rvl_result = {
    "rows": len(rvl_rows),
    "class_counts": dict(sorted(rvl_counts.items())),
    "missing_files": rvl_missing,
    "hash_errors": rvl_hash_errors,
    "corrupt_images": rvl_corrupt,
    "exact_duplicate_hashes": rvl_duplicate_hashes,
    "row_count_pass": len(rvl_rows) == EXPECTED["rvl_cdip"]["sample_rows"],
    "balance_pass": len(rvl_counts) == EXPECTED["rvl_cdip"]["classes"]
        and set(rvl_counts.values()) == {EXPECTED["rvl_cdip"]["per_class"]},
}
print("Rows:", rvl_result["rows"])
print("Classes:", rvl_result["class_counts"])
if not rvl_result["row_count_pass"] or not rvl_result["balance_pass"] or rvl_missing or rvl_hash_errors or rvl_corrupt:
    raise RuntimeError("RVL sample audit failed.")
print("RVL-CDIP sample: PASS")"""
        ),
        markdown("## 9. Kết luận tự động và các cổng thủ công"),
        code(
            """automated_checks = {
    "registry_and_manifests": not missing_sources and not manifest_errors,
    "cord": all([
        parquet_results["cord_v2"]["row_count_pass"],
        parquet_results["cord_v2"]["split_count_pass"],
        parquet_results["cord_v2"]["image_decode_pass"],
        parquet_results["cord_v2"]["leakage_pass"],
    ]),
    "sroie": all([
        parquet_results["sroie"]["row_count_pass"],
        parquet_results["sroie"]["split_count_pass"],
        parquet_results["sroie"]["image_decode_pass"],
        parquet_results["sroie"]["leakage_pass"],
    ]),
    "funsd": funsd_result["count_pass"] and funsd_result["pairing_pass"] and not funsd_corrupt,
    "xfund": xfund_result["asset_count_pass"] and not checksum_errors and not zip_errors and xfund_result["leakage_pass"],
    "rvl_sample": rvl_result["row_count_pass"] and rvl_result["balance_pass"]
        and not rvl_missing and not rvl_hash_errors and not rvl_corrupt,
}

manual_gates = {
    "pii_review": "required",
    "near_duplicate_review": "required_before_final_split",
    "license_review": {
        "cord_v2": "CC-BY-4.0",
        "sroie": "verify mirror against canonical CC-BY-4.0",
        "funsd": "research/education non-commercial",
        "xfund": "CC-BY-NC-SA-4.0",
        "rvl_cdip": "other; production use blocked pending legal review",
    },
    "production_training": "blocked_until_real_insurance_data_and_license_review",
}

audit = {
    "schema_version": 1,
    "created_at": utc_now(),
    "project": str(NEW_PROJECT),
    "automated_checks": automated_checks,
    "automated_audit_valid": all(automated_checks.values()),
    "research_baseline_gate": "ready" if all(automated_checks.values()) else "blocked",
    "commercial_production_gate": "blocked",
    "manual_gates": manual_gates,
    "cord_sroie": parquet_results,
    "funsd": funsd_result,
    "xfund": xfund_result,
    "rvl_cdip_sample": rvl_result,
    "midv": {
        "status": "deferred_by_scope",
        "reason": "ID-document branch has not started; metadata remains registered.",
    },
}
atomic_json(AUDIT_JSON, audit)

lines = [
    "# Document Data Audit v1",
    "",
    f"- Created: {audit['created_at']}",
    f"- Automated audit valid: **{audit['automated_audit_valid']}**",
    f"- Research baseline gate: **{audit['research_baseline_gate']}**",
    f"- Commercial production gate: **{audit['commercial_production_gate']}**",
    "",
    "## Automated checks",
    "",
]
for name, passed in automated_checks.items():
    lines.append(f"- {name}: {'PASS' if passed else 'FAIL'}")
lines += [
    "",
    "## Manual gates",
    "",
    "- PII review is required.",
    "- Near-duplicate review is required before the final split.",
    "- FUNSD/XFUND/RVL licensing blocks direct commercial production use pending review.",
    "- Public datasets do not replace labeled Vietnamese insurance documents.",
]
AUDIT_MD.write_text("\\n".join(lines) + "\\n", encoding="utf-8")

print("\\n=== DOCUMENT DATA AUDIT COMPLETED ===")
print(json.dumps(automated_checks, ensure_ascii=False, indent=2))
print("Automated audit valid:", audit["automated_audit_valid"])
print("Research baseline gate:", audit["research_baseline_gate"])
print("Commercial production gate:", audit["commercial_production_gate"])
print("Audit JSON:", AUDIT_JSON)
print("Audit report:", AUDIT_MD)"""
        ),
        markdown(
            """## 10. Sau audit

- Nếu `automated_audit_valid=True`, có thể bắt đầu tạo dataset Processed và benchmark nghiên cứu.
- Giữ `commercial_production_gate=blocked` cho tới khi hoàn tất legal/PII review và có dữ liệu chứng từ bảo hiểm thật.
- Gửi output cuối cùng cùng hai file audit. Notebook tiếp theo sẽ chuẩn hóa task và dựng baseline document classification/OCR/KIE; không dùng test split để chọn model."""
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
