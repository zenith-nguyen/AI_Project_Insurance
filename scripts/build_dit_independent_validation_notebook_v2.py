"""Build a DiT validation notebook that works with datasets >= 3.0."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_DiT_Independent_Validation_Acc2_v2.ipynb")


def cell(kind: str, value: str) -> dict:
    payload = {
        "cell_type": kind,
        "metadata": {},
        "source": [line + "\n" for line in value.strip("\n").split("\n")],
    }
    if kind == "code":
        payload.update(execution_count=None, outputs=[])
    return payload


def main() -> None:
    cells = [
        cell(
            "markdown",
            """# DiT Independent RVL-CDIP Validation — Acc 2 v2

Bản v2 bỏ local `rvl_cdip.py` vì `datasets>=3` không còn hỗ trợ dataset loading script. Notebook đọc mirror Parquet đã khóa revision, chỉ lấy split `val`, tạo sample cân bằng 20 ảnh × 16 lớp và cache 320 ảnh cùng SHA-256 trên Drive. Sample này độc lập với sample upstream `train` đã dùng trong smoke baseline. Final test không được đọc.""",
        ),
        cell(
            "code",
            '''from pathlib import Path
PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
RVL_ROOT = PROJECT / "data/bronze/documents/rvl_cdip/mirror_main"
CACHE_ROOT = RVL_ROOT / "independent_validation_sample_v1"
MANIFEST = CACHE_ROOT / "sample_manifest.jsonl"
REPORT = PROJECT / "reports/metrics/documents/dit_rvl_official_validation_v1.json"

MIRROR_ID = "chainyo/rvl-cdip"
MIRROR_REVISION = "66f430a1252ea1732413a80a56a1b6e8bc74264e"
SOURCE_SPLIT = "val"
MODEL_ID = "microsoft/dit-base-finetuned-rvlcdip"
MODEL_REVISION = "23f8b03d130fb66bbc9a15df3c75d753e49240eb"
SEED = 20261011
SAMPLES_PER_CLASS = 20
EXPECTED_CLASSES = 16
RUN_FINAL_TEST = False''',
        ),
        cell(
            "code",
            '''import importlib.util, subprocess, sys
requirements = {
    "datasets": "datasets>=3.0,<4",
    "transformers": "transformers>=4.45,<6",
    "sklearn": "scikit-learn>=1.5,<2",
    "PIL": "Pillow>=10,<13",
}
for module, requirement in requirements.items():
    if importlib.util.find_spec(module) is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", requirement], check=True)

from google.colab import drive
drive.mount("/content/drive")
if RUN_FINAL_TEST:
    raise RuntimeError("Notebook này chỉ chạy validation.")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
print("Environment: PASS")''',
        ),
        cell(
            "markdown",
            """## 1. Tạo hoặc tiếp tục sample validation

Lần đầu có thể đọc vài GB Parquet từ mirror vì ảnh nằm trong các shard lớn. Ảnh đã chọn được ghi ngay vào Drive; nếu runtime ngắt, chạy lại cell này để tiếp tục. Không tải archive 38,8 GB và không dùng `trust_remote_code`.""",
        ),
        cell(
            "code",
            '''from collections import Counter
from io import BytesIO
import hashlib, json
from datasets import load_dataset
from PIL import Image

CLASS_NAMES = [
    "advertisement", "budget", "email", "file folder", "form", "handwritten",
    "invoice", "letter", "memo", "news article", "presentation", "questionnaire",
    "resume", "scientific publication", "scientific report", "specification",
]

def read_manifest():
    if not MANIFEST.is_file():
        return []
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]

saved = read_manifest()
counts = Counter(row["class_name"] for row in saved)
known_hashes = {row["sha256"] for row in saved}

if any(counts[name] < SAMPLES_PER_CLASS for name in CLASS_NAMES):
    stream = load_dataset(
        MIRROR_ID,
        revision=MIRROR_REVISION,
        split=SOURCE_SPLIT,
        streaming=True,
    ).shuffle(seed=SEED, buffer_size=5000)
    label_names = stream.features["label"].names
    with MANIFEST.open("a", encoding="utf-8") as handle:
        for sequence, example in enumerate(stream):
            class_name = label_names[int(example["label"])]
            if counts[class_name] >= SAMPLES_PER_CLASS:
                if all(counts[name] >= SAMPLES_PER_CLASS for name in CLASS_NAMES):
                    break
                continue
            image = example["image"].convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            content = buffer.getvalue()
            digest = hashlib.sha256(content).hexdigest()
            if digest in known_hashes:
                continue
            destination = CACHE_ROOT / class_name.replace(" ", "_") / f"{digest}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            row = {
                "relative_path": str(destination.relative_to(CACHE_ROOT)),
                "class_name": class_name,
                "sha256": digest,
                "stream_sequence": sequence,
                "source_dataset": MIRROR_ID,
                "source_revision": MIRROR_REVISION,
                "source_split": SOURCE_SPLIT,
                "sample_seed": SEED,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\\n")
            handle.flush()
            saved.append(row)
            known_hashes.add(digest)
            counts[class_name] += 1
            print(f"Cached {sum(counts.values())}/{EXPECTED_CLASSES*SAMPLES_PER_CLASS}: {class_name} {counts[class_name]}/{SAMPLES_PER_CLASS}")
            if all(counts[name] >= SAMPLES_PER_CLASS for name in CLASS_NAMES):
                break

saved = read_manifest()
counts = Counter(row["class_name"] for row in saved)
expected = {name: SAMPLES_PER_CLASS for name in CLASS_NAMES}
if dict(sorted(counts.items())) != dict(sorted(expected.items())):
    raise RuntimeError(f"Validation cache incomplete; rerun this cell to resume: {counts}")
if len({row["sha256"] for row in saved}) != EXPECTED_CLASSES * SAMPLES_PER_CLASS:
    raise RuntimeError("Validation cache contains duplicate image hashes.")
print("Independent validation cache: PASS", dict(sorted(counts.items())))
print("Manifest:", MANIFEST)''',
        ),
        cell(
            "markdown",
            """## 2. Đánh giá checkpoint DiT đã pin

Metric này là validation độc lập với sample train của baseline v1. Nó vẫn là benchmark RVL-CDIP/mirror, chưa đại diện chứng từ bảo hiểm Việt Nam.""",
        ),
        cell(
            "code",
            '''from datetime import datetime, timezone
import torch
from sklearn.metrics import balanced_accuracy_score, classification_report, f1_score
from transformers import AutoImageProcessor, AutoModelForImageClassification

saved = read_manifest()
rows = [
    {"image": Image.open(CACHE_ROOT / row["relative_path"]).convert("RGB"), "class_name": row["class_name"]}
    for row in saved
]
processor = AutoImageProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForImageClassification.from_pretrained(MODEL_ID, revision=MODEL_REVISION).to(device).eval()
print("Device:", device)

truth, predicted = [], []
for start in range(0, len(rows), 16):
    batch = rows[start:start + 16]
    inputs = {k: v.to(model.device) for k, v in processor(images=[row["image"] for row in batch], return_tensors="pt").items()}
    with torch.inference_mode():
        ids = model(**inputs).logits.argmax(-1).cpu().tolist()
    truth.extend(row["class_name"] for row in batch)
    predicted.extend(model.config.id2label[index] for index in ids)

payload = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "model": MODEL_ID,
    "model_revision": MODEL_REVISION,
    "source_dataset": MIRROR_ID,
    "source_revision": MIRROR_REVISION,
    "source_split": SOURCE_SPLIT,
    "sample_seed": SEED,
    "samples_per_class": SAMPLES_PER_CLASS,
    "validation_rows": len(rows),
    "test_used": False,
    "sample_manifest": str(MANIFEST),
    "macro_f1": float(f1_score(truth, predicted, average="macro")),
    "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
    "classification_report": classification_report(truth, predicted, output_dict=True, zero_division=0),
    "limitations": [
        "Validation data comes from a pinned Hugging Face Parquet mirror of RVL-CDIP.",
        "This benchmark is not an insurance-domain or Vietnamese-document evaluation.",
        "Known RVL-CDIP label noise and overlap risks still apply.",
    ],
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("Independent macro-F1:", payload["macro_f1"])
print("Independent balanced accuracy:", payload["balanced_accuracy"])
print("Test used: False")
print("Report:", REPORT)''',
        ),
    ]
    payload = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    main()
