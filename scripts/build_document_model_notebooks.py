"""Build the Colab notebooks used for document and graph baselines."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks")


def _lines(value: str) -> list[str]:
    return [line + "\n" for line in value.strip("\n").split("\n")]


def md(value: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(value)}


def code(value: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(value),
    }


def write(name: str, cells: list[dict]) -> None:
    payload = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def baseline_cells() -> list[dict]:
    return [
        md(
            """# Document Baselines — Acc 2 v1

Chạy validation cho ba baseline độc lập: **DiT document classifier**, **PaddleOCR** và **KIE rule v1**. Test luôn khóa. Notebook dừng nếu SROIE processed split chưa PASS."""
        ),
        code(
            '''from pathlib import Path

PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
SROIE_REPORT = PROJECT / "reports/data_audit/documents/sroie_processed_split_v1.json"
SROIE_ROOT = PROJECT / "data/processed/documents/sroie/v1"
RVL_ROOT = PROJECT / "data/bronze/documents/rvl_cdip/mirror_main"
REPORT_ROOT = PROJECT / "reports/metrics/documents"
RUN_FINAL_TEST = False
SEED = 20261011
print("Final test locked:", not RUN_FINAL_TEST)'''
        ),
        code(
            '''import subprocess, sys

subprocess.run([
    sys.executable, "-m", "pip", "install", "-q", "paddlepaddle==3.2.0",
    "-i", "https://www.paddlepaddle.org.cn/packages/stable/cpu/",
], check=True)
subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "transformers>=4.45,<6", "accelerate>=1,<2", "paddleocr>=3,<4",
    "scikit-learn>=1.5,<2", "pyarrow>=17,<26", "Pillow>=10,<13",
], check=True)
from google.colab import drive
drive.mount("/content/drive")
import torch
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")'''
        ),
        code(
            '''import json
from datetime import datetime, timezone

split_report = json.loads(SROIE_REPORT.read_text(encoding="utf-8"))
overlaps = split_report.get("cross_split_exact_duplicates", {})
if not split_report.get("valid") or any(overlaps.values()):
    raise RuntimeError("SROIE processed split chưa PASS hoặc còn duplicate.")
if split_report.get("test_used_for_split_or_selection") or RUN_FINAL_TEST:
    raise RuntimeError("Test phải khóa trong model selection.")
REPORT_ROOT.mkdir(parents=True, exist_ok=True)
print("SROIE processed gate: PASS")'''
        ),
        md("## 1. DiT pretrained baseline trên 320 ảnh validation khóa từ RVL sample"),
        code(
            '''import random
from collections import defaultdict
from PIL import Image
from sklearn.metrics import balanced_accuracy_score, classification_report, f1_score
from transformers import AutoImageProcessor, AutoModelForImageClassification

rows = [json.loads(line) for line in (RVL_ROOT / "sample_manifest.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
by_class = defaultdict(list)
for row in rows:
    by_class[row["class_name"]].append(row)
rng = random.Random(SEED)
validation_rows = []
for label, items in sorted(by_class.items()):
    items = sorted(items, key=lambda item: item["sha256"])
    rng.shuffle(items)
    validation_rows.extend(items[:20])
if len(validation_rows) != 320:
    raise RuntimeError("RVL validation phải có 20 ảnh x 16 lớp.")

MODEL_ID = "microsoft/dit-base-finetuned-rvlcdip"
REVISION = "23f8b03d130fb66bbc9a15df3c75d753e49240eb"
processor = AutoImageProcessor.from_pretrained(MODEL_ID, revision=REVISION)
model = AutoModelForImageClassification.from_pretrained(MODEL_ID, revision=REVISION)
model = model.to("cuda" if torch.cuda.is_available() else "cpu").eval()
truth, predicted = [], []
for start in range(0, len(validation_rows), 16):
    batch = validation_rows[start:start + 16]
    images = [Image.open(RVL_ROOT / row["relative_path"]).convert("RGB") for row in batch]
    inputs = {key: value.to(model.device) for key, value in processor(images=images, return_tensors="pt").items()}
    with torch.inference_mode():
        ids = model(**inputs).logits.argmax(-1).cpu().tolist()
    truth.extend(row["class_name"] for row in batch)
    predicted.extend(model.config.id2label[index] for index in ids)

classifier_result = {
    "model": MODEL_ID,
    "revision": REVISION,
    "validation_rows": len(truth),
    "macro_f1": f1_score(truth, predicted, average="macro"),
    "balanced_accuracy": balanced_accuracy_score(truth, predicted),
    "classification_report": classification_report(truth, predicted, output_dict=True, zero_division=0),
    "limitation": "RVL sample may overlap upstream DiT data and is not an insurance-domain test.",
}
print("Classifier macro-F1:", classifier_result["macro_f1"])
print("Balanced accuracy:", classifier_result["balanced_accuracy"])'''
        ),
        md("## 2. PaddleOCR trên 93 validation receipt"),
        code(
            '''import io, time
import pyarrow.parquet as pq
from paddleocr import PaddleOCR

validation = pq.read_table(SROIE_ROOT / "validation.parquet").to_pylist()
ocr = PaddleOCR(lang="en")

def ground_truth_text(row):
    if isinstance(row.get("words"), list):
        return " ".join(str(word) for word in row["words"])
    for key in ("text", "transcription", "ocr"):
        if isinstance(row.get(key), str):
            return row[key]
    raise RuntimeError(f"Không tìm thấy ground-truth text. Columns: {sorted(row)}")

def paddle_text(results):
    tokens = []
    for result in results:
        payload = getattr(result, "json", result)
        if isinstance(payload, dict):
            payload = payload.get("res", payload)
            tokens.extend(payload.get("rec_texts", []))
    return " ".join(tokens)

def distance(left, right):
    previous = list(range(len(right) + 1))
    for row, a in enumerate(left, 1):
        current = [row]
        for column, b in enumerate(right, 1):
            current.append(min(current[-1]+1, previous[column]+1, previous[column-1]+(a != b)))
        previous = current
    return previous[-1]

references, hypotheses, elapsed = [], [], []
for index, row in enumerate(validation):
    value = row["image"]
    raw = value.get("bytes") if isinstance(value, dict) else value
    image_path = Path("/content/sroie_ocr_current.png")
    image_path.write_bytes(raw)
    started = time.perf_counter()
    hypotheses.append(paddle_text(list(ocr.predict(str(image_path)))))
    elapsed.append(time.perf_counter() - started)
    references.append(ground_truth_text(row))
    if (index + 1) % 10 == 0: print("OCR", index + 1, "/", len(validation))

ocr_result = {
    "engine": "PaddleOCR",
    "validation_rows": len(validation),
    "cer": sum(distance(list(a), list(b)) for a,b in zip(references,hypotheses)) / max(sum(map(len,references)),1),
    "wer": sum(distance(a.split(),b.split()) for a,b in zip(references,hypotheses)) / max(sum(len(x.split()) for x in references),1),
    "mean_seconds_per_page": sum(elapsed)/len(elapsed),
}
print(ocr_result)'''
        ),
        md("## 3. Rule KIE cho ngày và tổng tiền; lưu report validation"),
        code(
            '''import re
DATE = re.compile(r"\\b(?:\\d{1,2}[/-]){2}\\d{2,4}\\b")
AMOUNT = re.compile(r"(?:total|amount|grand total|tổng tiền|tổng cộng)\\s*[:：]?\\s*(?:VND|VNĐ|USD|\\$)?\\s*([0-9][0-9., ]{2,})", re.I)
normalize = lambda value: re.sub(r"[^a-z0-9]", "", str(value).lower())
expected, found = [], []
for row, text in zip(validation, hypotheses):
    entity = row.get("entities", {})
    entity = entity if isinstance(entity, dict) else {}
    for source, target in (("date","document_date"),("total","total_amount")):
        if entity.get(source): expected.append((target, normalize(entity[source])))
    date, amount = DATE.search(text), AMOUNT.search(text)
    if date: found.append(("document_date", normalize(date.group(0))))
    if amount: found.append(("total_amount", normalize(amount.group(1))))
expected_set, found_set = set(expected), set(found)
true_positive = len(expected_set & found_set)
precision = true_positive / len(found_set) if found_set else 0.0
recall = true_positive / len(expected_set) if expected_set else 0.0
kie_result = {"baseline":"document-rule-kie-v1", "precision":precision, "recall":recall, "micro_f1":2*precision*recall/(precision+recall) if precision+recall else 0.0, "evaluated_fields":["document_date","total_amount"]}
payload = {"created_at":datetime.now(timezone.utc).isoformat(), "split":"validation", "test_used":False, "classifier":classifier_result, "ocr":ocr_result, "kie":kie_result}
output = REPORT_ROOT / "document_baselines_validation_v1.json"
output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("Document baseline report:", output)
print(json.dumps({"classifier":classifier_result,"ocr":ocr_result,"kie":kie_result}, ensure_ascii=False, indent=2))'''
        ),
        md("Gửi toàn bộ output và file JSON cuối. Không mở test. Sau đó mới chạy notebook LayoutLMv3 candidate."),
    ]


def graph_cells() -> list[dict]:
    return [
        md(
            """# Claim Consistency + NetworkX Demo — Acc 2 v1

Kiểm tra code bằng dữ liệu giả lập có `claim_id` và timestamp. Đây là engineering demo, không phải metric phát hiện fraud."""
        ),
        code(
            '''import subprocess, sys
subprocess.run([sys.executable,"-m","pip","install","-q","networkx>=3.3,<4"], check=True)
import networkx as nx
from datetime import datetime

cutoff = datetime.fromisoformat("2026-10-11T12:00:00+00:00")
nodes = [
 {"id":"CLM-001","entity_type":"claim","available_at":"2026-10-01T00:00:00+00:00"},
 {"id":"CLM-002","entity_type":"claim","available_at":"2026-10-02T00:00:00+00:00"},
 {"id":"PHONE-01","entity_type":"phone","available_at":"2026-09-01T00:00:00+00:00"},
]
edges = [
 {"source":"CLM-001","target":"PHONE-01","relation":"uses","event_time":"2026-10-01T01:00:00+00:00"},
 {"source":"CLM-002","target":"PHONE-01","relation":"uses","event_time":"2026-10-02T01:00:00+00:00"},
]
graph = nx.Graph()
for node in nodes:
    if datetime.fromisoformat(node["available_at"]) <= cutoff: graph.add_node(node["id"], **node)
for edge in edges:
    if datetime.fromisoformat(edge["event_time"]) <= cutoff: graph.add_edge(edge["source"], edge["target"], **edge)
features = {
 "graph_degree":graph.degree("CLM-001"),
 "shared_entity_count":sum(graph.degree(x)>1 for x in graph.neighbors("CLM-001")),
 "connected_component_size":len(nx.node_connected_component(graph,"CLM-001")),
 "two_hop_claim_count":len({n for x in graph.neighbors("CLM-001") for n in graph.neighbors(x) if n!="CLM-001" and graph.nodes[n]["entity_type"]=="claim"}),
}
assert features == {"graph_degree":1,"shared_entity_count":1,"connected_component_size":3,"two_hop_claim_count":1}
print("Point-in-time graph demo: PASS", features)'''
        ),
        code(
            '''def amount_check(claim_amount, document_amount, confidence, tolerance=0.05):
    if document_amount is None or confidence < 0.5:
        return {"status":"unknown", "reason":"missing_or_low_confidence"}
    ratio = abs(document_amount-claim_amount)/max(abs(claim_amount),1)
    return {"status":"pass" if ratio<=tolerance else "fail", "difference":document_amount-claim_amount}

assert amount_check(10_000_000,10_200_000,0.9)["status"] == "pass"
assert amount_check(10_000_000,12_000_000,0.9)["status"] == "fail"
assert amount_check(10_000_000,None,0.0)["status"] == "unknown"
print("Consistency demo: PASS")'''
        ),
        md("Dữ liệu thật cần claim/entity/edge có timestamp. Không ghép các public dataset theo dòng để tạo graph giả."),
    ]


def main() -> None:
    write("Document_Baselines_Acc2_v1.ipynb", baseline_cells())
    write("Claim_Consistency_NetworkX_Demo_Acc2_v1.ipynb", graph_cells())
    print("Built document baseline and graph demo notebooks")


if __name__ == "__main__":
    main()
