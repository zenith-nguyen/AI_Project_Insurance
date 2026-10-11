"""Build the governed Colab intake notebook for public document datasets."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_Data_Intake_Acc2_v1.ipynb")


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
            """# Document Data Intake — Acc2 v1

Notebook này gom dữ liệu chứng từ vào một Bronze registry có version, nguồn, license và checksum. Chạy bằng **CPU runtime**. Các nguồn lớn không tự tải nếu chưa bật cờ và chưa đủ dung lượng.

Không đưa Kaggle/Hugging Face token vào cell. Nếu cần, lưu token trong **Colab Secrets**."""
        ),
        markdown("## 1. Cấu hình tải"),
        code(
            """from pathlib import Path

NEW_PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
BRONZE_ROOT = NEW_PROJECT / "data/bronze/documents"
REGISTRY_ROOT = NEW_PROJECT / "data/registry/documents"
QUARANTINE_ROOT = NEW_PROJECT / "data/quarantine/documents"
AUDIT_ROOT = NEW_PROJECT / "reports/data_audit/documents"

# Nguồn nhỏ/vừa: tải mặc định.
DOWNLOAD_CORD_V2 = True
DOWNLOAD_FUNSD = True
DOWNLOAD_XFUND = True

# SROIE: chọn một trong hai cách và pin version.
SROIE_ARCHIVE_ON_DRIVE = ""  # Ví dụ: /content/drive/MyDrive/downloads/sroie.zip
SROIE_KAGGLE_HANDLE = ""     # Bắt buộc dạng owner/dataset/versions/N
# Fallback công khai đã hiệu chỉnh; nguồn gốc vẫn là ICDAR 2019 RRC.
DOWNLOAD_SROIE_HF_MIRROR = True
SROIE_HF_REPO = "jsdnrs/ICDAR2019-SROIE"
SROIE_HF_REVISION = "bffe40c26759f3376ec2b3ae9031dbba54cd587c"

# Nguồn lớn: chỉ bật sau khi xem bảng dung lượng ở cuối notebook.
ALLOW_LARGE_DOWNLOADS = False
DOWNLOAD_MIDV500_ALL = False       # khoảng 32.9 GB
DOWNLOAD_MIDV2020_CORE = False     # khoảng 7.1 GB, không gồm clips.tar
DOWNLOAD_MIDV2020_CLIPS = False    # thêm khoảng 10.3 GB
DOWNLOAD_RVL_CDIP_FULL = False     # khoảng 38.8 GB

# Sample RVL-CDIP dùng cho baseline classification nhỏ.
DOWNLOAD_RVL_CDIP_SAMPLE = True
RVL_SAMPLE_PER_CLASS = 100
RVL_SAMPLE_SEED = 20261010

print("Project:", NEW_PROJECT)
print("Large downloads enabled:", ALLOW_LARGE_DOWNLOADS)"""
        ),
        markdown("## 2. Mount Drive và cài thư viện"),
        code(
            """import importlib
import subprocess
import sys

from google.colab import drive

if not Path("/content/drive/MyDrive").is_dir():
    drive.mount("/content/drive")

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "huggingface_hub>=0.35,<2",
        "datasets>=3.6,<4",
        "kagglehub>=1,<2",
        "Pillow>=10,<13",
        "PyYAML>=6,<7",
        "requests>=2.32,<3",
        "tqdm>=4.66,<5",
    ],
    check=True,
)
importlib.invalidate_caches()

import datasets
import huggingface_hub
import kagglehub
import requests
from PIL import Image

print("datasets:", datasets.__version__)
print("huggingface_hub:", huggingface_hub.__version__)
print("Environment: PASS")"""
        ),
        markdown("## 3. Helper an toàn, registry và kiểm tra dung lượng"),
        code(
            """import hashlib
import json
import os
import shutil
import time
import zipfile
from datetime import datetime, timezone

from tqdm.auto import tqdm


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def sha256_file(path: Path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.md5()  # Used only to verify checksums published by Zenodo.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_gb(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free / (1024 ** 3)


def require_space(required_gb: float, label: str):
    available = free_gb(NEW_PROJECT)
    if available < required_gb:
        raise RuntimeError(
            f"Không đủ dung lượng cho {label}: cần tối thiểu {required_gb:.1f} GB, "
            f"còn {available:.1f} GB."
        )
    print(f"Disk gate {label}: PASS ({available:.1f} GB free)")


def download_file(url: str, destination: Path, expected_size=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and (
        expected_size is None or destination.stat().st_size == expected_size
    ):
        print("Reuse:", destination)
        return destination
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    with requests.get(url, stream=True, timeout=(30, 120)) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0)) or expected_size
        with partial.open("wb") as handle, tqdm(
            total=total, unit="B", unit_scale=True, desc=destination.name
        ) as progress:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    progress.update(len(chunk))
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise IOError(
            f"Sai kích thước {destination.name}: {partial.stat().st_size} != {expected_size}"
        )
    os.replace(partial, destination)
    return destination


def safe_extract_zip(archive: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"Unsafe ZIP member: {member.filename}")
        handle.extractall(destination)


def source_dir(name: str, version: str):
    path = BRONZE_ROOT / name / version
    (path / "raw").mkdir(parents=True, exist_ok=True)
    return path


def write_manifest(root: Path, payload: dict):
    payload = {**payload, "manifest_written_at": utc_now()}
    atomic_json(root / "source_manifest.json", payload)
    return payload


for directory in [BRONZE_ROOT, REGISTRY_ROOT, QUARANTINE_ROOT, AUDIT_ROOT]:
    directory.mkdir(parents=True, exist_ok=True)

print("Free Drive GB:", round(free_gb(NEW_PROJECT), 2))
print("Data directories: PASS")"""
        ),
        markdown("## 4. CORD v2 — Hugging Face chính thức, pin revision"),
        code(
            """from huggingface_hub import snapshot_download

if DOWNLOAD_CORD_V2:
    root = source_dir("cord_v2", "v2")
    revision = "41b075798d0d9da590a950dac1e3d4a21826d4fd"
    require_space(3.2, "CORD v2")
    snapshot_path = snapshot_download(
        repo_id="naver-clova-ix/cord-v2",
        repo_type="dataset",
        revision=revision,
        local_dir=root / "raw/huggingface_snapshot",
    )
    write_manifest(
        root,
        {
            "dataset_name": "cord_v2",
            "version": "v2",
            "status": "downloaded",
            "source_url": "https://huggingface.co/datasets/naver-clova-ix/cord-v2",
            "acquisition_method": "huggingface_snapshot",
            "revision": revision,
            "license": "CC-BY-4.0",
            "expected_examples": 1000,
            "expected_splits": {"train": 800, "validation": 100, "test": 100},
            "local_path": str(snapshot_path),
        },
    )
    print("CORD v2 intake: PASS")
else:
    print("CORD v2: SKIPPED")"""
        ),
        markdown("## 5. FUNSD — archive chính thức"),
        code(
            """if DOWNLOAD_FUNSD:
    root = source_dir("funsd", "original_2019")
    archive_url = "https://guillaumejaume.github.io/FUNSD/dataset.zip"
    archive = download_file(archive_url, root / "raw/dataset.zip")
    extracted = root / "raw/extracted"
    marker = extracted / ".extraction_complete"
    if not marker.is_file():
        safe_extract_zip(archive, extracted)
        marker.write_text(utc_now(), encoding="utf-8")
    write_manifest(
        root,
        {
            "dataset_name": "funsd",
            "version": "original_2019",
            "status": "downloaded",
            "source_url": "https://guillaumejaume.github.io/FUNSD/",
            "archive_url": archive_url,
            "archive_sha256": sha256_file(archive),
            "license": "non-commercial-research-education",
            "terms_url": "https://guillaumejaume.github.io/FUNSD/work/",
            "expected_examples": 199,
        },
    )
    print("FUNSD intake: PASS")
else:
    print("FUNSD: SKIPPED")"""
        ),
        markdown("## 6. XFUND v1.0 — release chính thức của Microsoft"),
        code(
            """if DOWNLOAD_XFUND:
    root = source_dir("xfund", "v1.0")
    release_api = "https://api.github.com/repos/doc-analysis/XFUND/releases/tags/v1.0"
    response = requests.get(release_api, timeout=60)
    response.raise_for_status()
    release = response.json()
    assets = release.get("assets", [])
    if not assets:
        raise RuntimeError("GitHub release v1.0 không trả asset.")
    downloaded_assets = []
    for asset in tqdm(assets, desc="XFUND assets"):
        destination = root / "raw/release_assets" / asset["name"]
        download_file(
            asset["browser_download_url"], destination, int(asset["size"])
        )
        downloaded_assets.append(
            {
                "name": asset["name"],
                "size": int(asset["size"]),
                "sha256": sha256_file(destination),
            }
        )
    write_manifest(
        root,
        {
            "dataset_name": "xfund",
            "version": "v1.0",
            "status": "downloaded",
            "source_url": "https://github.com/doc-analysis/XFUND/releases/tag/v1.0",
            "release_id": release.get("id"),
            "release_tag": release.get("tag_name"),
            "license": "CC-BY-NC-SA-4.0",
            "languages": ["zh", "ja", "es", "fr", "it", "de", "pt"],
            "assets": downloaded_assets,
        },
    )
    print("XFUND intake: PASS")
else:
    print("XFUND: SKIPPED")"""
        ),
        markdown(
            """## 7. SROIE — RRC hoặc mirror đã pin

Ưu tiên tải archive từ RRC rồi đặt đường dẫn vào `SROIE_ARCHIVE_ON_DRIVE`. Nếu dùng Kaggle, handle phải có `/versions/N`; notebook không chấp nhận `latest` không được ghi version. Khi cả hai trường để trống, notebook dùng mirror Hugging Face đã hiệu chỉnh và ghim commit; manifest vẫn lưu RRC là nguồn gốc."""
        ),
        code(
            """sroie_root = source_dir("sroie", "ICDAR2019")
if SROIE_ARCHIVE_ON_DRIVE:
    source_archive = Path(SROIE_ARCHIVE_ON_DRIVE)
    if not source_archive.is_file():
        raise FileNotFoundError(source_archive)
    destination = sroie_root / "raw" / source_archive.name
    if not destination.is_file() or destination.stat().st_size != source_archive.stat().st_size:
        shutil.copy2(source_archive, destination)
    write_manifest(
        sroie_root,
        {
            "dataset_name": "sroie",
            "version": "ICDAR2019",
            "status": "registered_from_manual_archive",
            "source_url": "https://rrc.cvc.uab.es/?ch=13&com=downloads",
            "archive_name": destination.name,
            "archive_size": destination.stat().st_size,
            "archive_sha256": sha256_file(destination),
            "license": "verify-from-RRC",
        },
    )
    print("SROIE manual archive: PASS")
elif SROIE_KAGGLE_HANDLE:
    if "/versions/" not in SROIE_KAGGLE_HANDLE:
        raise ValueError("SROIE_KAGGLE_HANDLE phải pin /versions/N")
    output = kagglehub.dataset_download(
        SROIE_KAGGLE_HANDLE,
        output_dir=str(sroie_root / "raw/kaggle_mirror"),
    )
    write_manifest(
        sroie_root,
        {
            "dataset_name": "sroie",
            "version": "ICDAR2019",
            "status": "downloaded_from_kaggle_mirror_pending_audit",
            "source_url": "https://rrc.cvc.uab.es/?ch=13&com=downloads",
            "kaggle_handle": SROIE_KAGGLE_HANDLE,
            "local_path": str(output),
            "license": "verify-from-selected-mirror-and-RRC",
        },
    )
    print("SROIE Kaggle mirror: DOWNLOADED, AUDIT REQUIRED")
elif DOWNLOAD_SROIE_HF_MIRROR:
    from huggingface_hub import snapshot_download

    output = snapshot_download(
        repo_id=SROIE_HF_REPO,
        repo_type="dataset",
        revision=SROIE_HF_REVISION,
        local_dir=sroie_root / "raw/huggingface_corrected_mirror",
        allow_patterns=[
            "data/*.parquet",
            "README.md",
            "LICENSE",
            "NOTICE",
        ],
    )
    write_manifest(
        sroie_root,
        {
            "dataset_name": "sroie",
            "version": "ICDAR2019-corrected-hf-mirror",
            "status": "downloaded_from_huggingface_mirror_pending_audit",
            "canonical_source_url": "https://rrc.cvc.uab.es/?ch=13&com=downloads",
            "mirror_url": f"https://huggingface.co/datasets/{SROIE_HF_REPO}",
            "mirror_repo": SROIE_HF_REPO,
            "mirror_revision": SROIE_HF_REVISION,
            "local_path": str(output),
            "expected_train_examples": 626,
            "expected_test_examples": 361,
            "expected_total_examples": 987,
            "license": "CC-BY-4.0-verify-during-audit",
        },
    )
    print("SROIE corrected Hugging Face mirror: PASS, AUDIT REQUIRED")
else:
    write_manifest(
        sroie_root,
        {
            "dataset_name": "sroie",
            "version": "ICDAR2019",
            "status": "awaiting_source_archive_or_pinned_kaggle_handle",
            "source_url": "https://rrc.cvc.uab.es/?ch=13&com=downloads",
        },
    )
    print("SROIE: WAITING FOR RRC ARCHIVE OR PINNED MIRROR")"""
        ),
        markdown("## 8. MIDV — inventory Zenodo và tải có gate"),
        code(
            """def zenodo_inventory(record_id: int, root: Path):
    api_url = f"https://zenodo.org/api/records/{record_id}"
    response = requests.get(api_url, timeout=120)
    response.raise_for_status()
    record = response.json()
    atomic_json(root / "zenodo_record.json", record)
    files = []
    for item in record.get("files", []):
        files.append(
            {
                "name": item["key"],
                "size": int(item["size"]),
                "checksum": item.get("checksum"),
                "url": item["links"]["self"],
            }
        )
    return record, files


def download_zenodo_files(root: Path, files: list, selected_names: set):
    selected = [item for item in files if item["name"] in selected_names]
    required_gb = sum(item["size"] for item in selected) / (1024 ** 3) * 1.2
    require_space(required_gb, root.name)
    completed = []
    for item in selected:
        destination = download_file(
            item["url"], root / "raw/zenodo" / item["name"], item["size"]
        )
        checksum = item.get("checksum") or ""
        if checksum.startswith("md5:"):
            expected_md5 = checksum.split(":", 1)[1]
            actual_md5 = md5_file(destination)
            if actual_md5 != expected_md5:
                raise RuntimeError(f"MD5 mismatch: {item['name']}")
        completed.append({**item, "local_path": str(destination)})
    return completed


midv500_root = source_dir("midv500", "v1")
midv500_record, midv500_files = zenodo_inventory(18504926, midv500_root)
midv500_downloaded = []
if DOWNLOAD_MIDV500_ALL:
    if not ALLOW_LARGE_DOWNLOADS:
        raise RuntimeError("Bật ALLOW_LARGE_DOWNLOADS trước khi tải MIDV-500.")
    midv500_downloaded = download_zenodo_files(
        midv500_root, midv500_files, {item["name"] for item in midv500_files}
    )
write_manifest(
    midv500_root,
    {
        "dataset_name": "midv500",
        "version": "v1",
        "status": "downloaded" if midv500_downloaded else "remote_inventory_only",
        "source_url": "https://zenodo.org/records/18504926",
        "zenodo_record": 18504926,
        "remote_files": midv500_files,
        "downloaded_files": midv500_downloaded,
    },
)

midv2020_root = source_dir("midv2020", "v1")
midv2020_record, midv2020_files = zenodo_inventory(18786808, midv2020_root)
selected_2020 = {"license.txt", "md5.txt", "readme.txt"}
if DOWNLOAD_MIDV2020_CORE:
    selected_2020 |= {
        "templates.tar",
        "scan_upright.tar",
        "scan_rotated.tar",
        "photo.tar",
    }
if DOWNLOAD_MIDV2020_CLIPS:
    selected_2020.add("clips.tar")
if (DOWNLOAD_MIDV2020_CORE or DOWNLOAD_MIDV2020_CLIPS) and not ALLOW_LARGE_DOWNLOADS:
    raise RuntimeError("Bật ALLOW_LARGE_DOWNLOADS trước khi tải MIDV-2020 data.")
midv2020_downloaded = download_zenodo_files(
    midv2020_root, midv2020_files, selected_2020
)
write_manifest(
    midv2020_root,
    {
        "dataset_name": "midv2020",
        "version": "v1",
        "status": "partially_downloaded",
        "source_url": "https://zenodo.org/records/18786808",
        "full_source_url": "https://l3i-share.univ-lr.fr/MIDV2020/midv2020.html",
        "zenodo_record": 18786808,
        "remote_files": midv2020_files,
        "downloaded_files": midv2020_downloaded,
    },
)
print("MIDV registry: PASS")"""
        ),
        markdown("## 9. RVL-CDIP — sample mặc định hoặc full archive có gate"),
        code(
            """rvl_root = source_dir("rvl_cdip", "mirror_main")
rvl_status = "registered"
rvl_details = {}

if DOWNLOAD_RVL_CDIP_SAMPLE:
    from datasets import load_dataset
    from huggingface_hub import hf_hub_download

    sample_root = rvl_root / "sample_raw"
    sample_root.mkdir(parents=True, exist_ok=True)
    sample_manifest = rvl_root / "sample_manifest.jsonl"
    if sample_manifest.is_file():
        print("RVL sample manifest đã có; không lấy mẫu lại:", sample_manifest)
        rvl_status = "sample_exists"
    else:
        try:
            # The upstream dataset script still points to the historical,
            # namespace-less `datasets/rvl_cdip` URLs. Newer huggingface_hub
            # rejects that redirect as an invalid hf:// URI. Keep the source
            # script intact in the HF cache and create a small, auditable local
            # compatibility copy with the canonical namespace.
            upstream_script = Path(
                hf_hub_download(
                    repo_id="aharley/rvl_cdip",
                    repo_type="dataset",
                    filename="rvl_cdip.py",
                )
            )
            patched_script = rvl_root / "loader_compat" / "rvl_cdip.py"
            patched_script.parent.mkdir(parents=True, exist_ok=True)
            script_text = upstream_script.read_text(encoding="utf-8")
            historical_prefix = (
                "https://huggingface.co/datasets/rvl_cdip/resolve/main/"
            )
            canonical_prefix = (
                "https://huggingface.co/datasets/aharley/rvl_cdip/resolve/main/"
            )
            replacement_count = script_text.count(historical_prefix)
            if replacement_count != 4:
                raise RuntimeError(
                    "RVL loader upstream changed; expected 4 historical URLs, "
                    f"found {replacement_count}. Stop for source audit."
                )
            patched_script.write_text(
                script_text.replace(historical_prefix, canonical_prefix),
                encoding="utf-8",
            )
            stream = load_dataset(
                str(patched_script),
                split="train",
                streaming=True,
                trust_remote_code=True,
            ).shuffle(seed=RVL_SAMPLE_SEED, buffer_size=5000)
            label_names = stream.features["label"].names
            counts = {index: 0 for index in range(len(label_names))}
            rows = []
            for example in stream:
                label = int(example["label"])
                if counts[label] >= RVL_SAMPLE_PER_CLASS:
                    continue
                class_name = label_names[label].replace(" ", "_")
                destination = (
                    sample_root / class_name / f"{counts[label]:05d}.png"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                image = example["image"].convert("RGB")
                image.save(destination)
                rows.append(
                    {
                        "relative_path": str(destination.relative_to(rvl_root)),
                        "label": label,
                        "class_name": label_names[label],
                        "sha256": sha256_file(destination),
                    }
                )
                counts[label] += 1
                if all(value >= RVL_SAMPLE_PER_CLASS for value in counts.values()):
                    break
            if not all(value == RVL_SAMPLE_PER_CLASS for value in counts.values()):
                raise RuntimeError(f"RVL sample chưa cân bằng: {counts}")
            temporary = sample_manifest.with_suffix(".jsonl.tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\\n")
            temporary.replace(sample_manifest)
            rvl_status = "balanced_sample_downloaded_pending_pii_and_duplicate_audit"
            rvl_details["sample_counts"] = {
                label_names[index]: count for index, count in counts.items()
            }
            rvl_details["loader_compatibility_patch"] = {
                "upstream_repo": "aharley/rvl_cdip",
                "historical_url_replacements": replacement_count,
                "patched_script_sha256": sha256_file(patched_script),
            }
            print("RVL balanced sample: PASS")
        except Exception as error:
            rvl_status = "sample_blocked"
            rvl_details["sample_error"] = repr(error)
            print("RVL sample chưa tải được:", repr(error))
            print("Giữ nguyên registry; không tự chuyển sang tải full 38.8 GB.")

if DOWNLOAD_RVL_CDIP_FULL:
    if not ALLOW_LARGE_DOWNLOADS:
        raise RuntimeError("Bật ALLOW_LARGE_DOWNLOADS trước khi tải full RVL-CDIP.")
    require_space(50.0, "RVL-CDIP full")
    full_path = snapshot_download(
        repo_id="aharley/rvl_cdip",
        repo_type="dataset",
        local_dir=rvl_root / "raw/huggingface_snapshot",
    )
    rvl_status = "full_mirror_downloaded_pending_pii_and_duplicate_audit"
    rvl_details["full_path"] = str(full_path)

write_manifest(
    rvl_root,
    {
        "dataset_name": "rvl_cdip",
        "version": "mirror_main",
        "status": rvl_status,
        "source_url": "https://huggingface.co/datasets/aharley/rvl_cdip",
        "license": "other-review-required",
        "expected_examples": 400000,
        "expected_classes": 16,
        "known_risks": ["label_noise", "train_test_overlap", "PII"],
        **rvl_details,
    },
)
print("RVL registry status:", rvl_status)"""
        ),
        markdown("## 10. Inventory tổng và registry"),
        code(
            """def directory_inventory(root: Path):
    files = [path for path in root.rglob("*") if path.is_file()]
    by_extension = {}
    total_bytes = 0
    for path in files:
        extension = path.suffix.lower() or "<none>"
        by_extension[extension] = by_extension.get(extension, 0) + 1
        total_bytes += path.stat().st_size
    return {
        "path": str(root),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "total_gb": total_bytes / (1024 ** 3),
        "by_extension": dict(sorted(by_extension.items())),
    }


source_manifests = sorted(BRONZE_ROOT.glob("*/*/source_manifest.json"))
registry = {
    "schema_version": 1,
    "created_at": utc_now(),
    "project": str(NEW_PROJECT),
    "free_drive_gb": free_gb(NEW_PROJECT),
    "sources": [],
}
for manifest_path in source_manifests:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_root = manifest_path.parent
    registry["sources"].append(
        {**manifest, "inventory": directory_inventory(dataset_root)}
    )

registry_path = REGISTRY_ROOT / "document_sources_registry.json"
atomic_json(registry_path, registry)
run_path = REGISTRY_ROOT / "intake_runs" / (
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
)
atomic_json(run_path, registry)

print("\\n=== DOCUMENT DATA INTAKE COMPLETED ===")
for item in registry["sources"]:
    inventory = item["inventory"]
    print(
        f"{item['dataset_name']}: {item.get('status')} | "
        f"{inventory['file_count']} files | {inventory['total_gb']:.2f} GB"
    )
print("Registry:", registry_path)
print("Run record:", run_path)
print("Free Drive GB:", round(free_gb(NEW_PROJECT), 2))"""
        ),
        markdown(
            """## 11. Sau khi chạy — cổng chuyển từ intake sang model

1. Lưu output `DOCUMENT DATA INTAKE COMPLETED` và `document_sources_registry.json`.
2. Xử lý mọi source còn `awaiting`, `sample_blocked` hoặc `pending_audit`.
3. Chạy license, PII, duplicate/near-duplicate và leakage audit.
4. Khóa task riêng cho document classification, OCR và key-information extraction.
5. Tạo split train/validation/test theo nguồn và document identity; không nối theo từng dòng với CarDD.
6. Chỉ sau khi các cổng trên PASS mới chạy baseline document model.

Nếu cần tải full MIDV/RVL, bật `ALLOW_LARGE_DOWNLOADS` cùng đúng cờ dataset sau khi xác nhận Drive còn đủ dung lượng. Public document datasets phục vụ pretraining/benchmark; dữ liệu bảo hiểm thật chỉ hợp nhất với CarDD/graph khi có `claim_id` hợp lệ."""
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
