"""Build the guarded LayoutLMv3 SROIE KIE candidate notebook."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_LayoutLMv3_Candidate_Acc2_v1.ipynb")


def lines(value: str) -> list[str]:
    return [line + "\n" for line in value.strip("\n").split("\n")]


def markdown(value: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": lines(value)}


def code(value: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(value)}


def main() -> None:
    cells = [
        markdown(
            """# LayoutLMv3 KIE Candidate — Acc 2 v1

Fine-tune candidate trên **train 525** và chọn bằng **validation 93** của processed SROIE. Test 361 luôn khóa. BIO labels được weak-align từ entity ground truth sang chuỗi OCR words; report phải nêu rõ giới hạn này."""
        ),
        code(
            '''from pathlib import Path

PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
DATA_ROOT = PROJECT / "data/processed/documents/sroie/v1"
BASELINE_REPORT = PROJECT / "reports/metrics/documents/document_baselines_validation_v1.json"
SPLIT_REPORT = PROJECT / "reports/data_audit/documents/sroie_processed_split_v1.json"
OUTPUT_ROOT = PROJECT / "artifacts/document/layoutlmv3_sroie_candidate_v1"
REPORT_PATH = PROJECT / "reports/metrics/documents/layoutlmv3_sroie_candidate_validation_v1.json"
RUN_FINAL_TEST = False
SEED = 20261011'''
        ),
        code(
            '''import subprocess, sys
subprocess.run([sys.executable,"-m","pip","install","-q","transformers>=4.45,<6","accelerate>=1,<2","seqeval>=1.2,<2","pyarrow>=17,<26","Pillow>=10,<13"], check=True)
from google.colab import drive
drive.mount("/content/drive")
import json
split_report = json.loads(SPLIT_REPORT.read_text(encoding="utf-8"))
if not BASELINE_REPORT.is_file(): raise FileNotFoundError("Chạy Document_Baselines trước.")
if not split_report.get("valid") or any(split_report["cross_split_exact_duplicates"].values()): raise RuntimeError("Processed split chưa sạch.")
if RUN_FINAL_TEST: raise RuntimeError("Giữ final test khóa trong model selection.")
print("Candidate gates: PASS")'''
        ),
        markdown("## 1. Căn chỉnh entity ground truth thành BIO labels"),
        code(
            '''import io, re
import numpy as np
import pyarrow.parquet as pq
import torch
from PIL import Image
from torch.utils.data import Dataset
from transformers import AutoProcessor, LayoutLMv3ForTokenClassification, Trainer, TrainingArguments, set_seed

set_seed(SEED)
FIELD_MAP = {"company":"COMPANY","date":"DATE","address":"ADDRESS","total":"TOTAL"}
LABELS = ["O"] + [prefix+"-"+name for name in FIELD_MAP.values() for prefix in ("B","I")]
LABEL2ID = {label:index for index,label in enumerate(LABELS)}
ID2LABEL = {index:label for label,index in LABEL2ID.items()}
normalize = lambda value: re.sub(r"\\W", "", str(value).lower())

def weak_bio(words, entities):
    labels = ["O"] * len(words)
    normalized_words = [normalize(word) for word in words]
    for source, target in FIELD_MAP.items():
        value = entities.get(source) if isinstance(entities, dict) else None
        if not value: continue
        wanted = normalize(value)
        for start in range(len(words)):
            built = ""
            for end in range(start, min(len(words), start+30)):
                built += normalized_words[end]
                if built == wanted:
                    labels[start] = "B-"+target
                    for index in range(start+1,end+1): labels[index] = "I-"+target
                    break
                if not wanted.startswith(built): break
            if labels[start] != "O": break
    return labels

BASE_MODEL = "microsoft/layoutlmv3-base"
BASE_REVISION = "4dcbeabd3db1a13c8aeead201bb7a4811904f1fd"
processor = AutoProcessor.from_pretrained(BASE_MODEL, revision=BASE_REVISION, apply_ocr=False)

class SROIE(Dataset):
    def __init__(self, path): self.rows = pq.read_table(path).to_pylist()
    def __len__(self): return len(self.rows)
    def __getitem__(self, index):
        row = self.rows[index]
        words = [str(word) for word in row["words"]]
        value = row["image"]; raw = value.get("bytes") if isinstance(value,dict) else value
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        boxes = row.get("bboxes") or row.get("boxes")
        if boxes is None: raise RuntimeError(f"Missing bboxes. Columns: {sorted(row)}")
        width,height = image.size
        boxes = [[max(0,min(1000,round(1000*x1/width))),max(0,min(1000,round(1000*y1/height))),max(0,min(1000,round(1000*x2/width))),max(0,min(1000,round(1000*y2/height)))] for x1,y1,x2,y2 in boxes]
        word_labels = [LABEL2ID[label] for label in weak_bio(words,row.get("entities",{}))]
        encoded = processor(image,words,boxes=boxes,word_labels=word_labels,truncation=True,padding="max_length",max_length=512,return_tensors="pt")
        return {key:value.squeeze(0) for key,value in encoded.items()}

train_data = SROIE(DATA_ROOT/"train.parquet")
validation_data = SROIE(DATA_ROOT/"validation.parquet")
if (len(train_data),len(validation_data)) != (525,93): raise RuntimeError("Unexpected processed row counts.")
print("Rows:",len(train_data),len(validation_data),"Test read: False")'''
        ),
        markdown("## 2. Fine-tune và chọn checkpoint trên validation"),
        code(
            '''from seqeval.metrics import f1_score, precision_score, recall_score

model = LayoutLMv3ForTokenClassification.from_pretrained(BASE_MODEL,revision=BASE_REVISION,num_labels=len(LABELS),id2label=ID2LABEL,label2id=LABEL2ID)
def compute_metrics(result):
    predictions = np.argmax(result.predictions,axis=-1)
    truth,predicted = [],[]
    for pred_row,label_row in zip(predictions,result.label_ids):
        keep = label_row != -100
        truth.append([ID2LABEL[int(x)] for x in label_row[keep]])
        predicted.append([ID2LABEL[int(x)] for x in pred_row[keep]])
    return {"precision":precision_score(truth,predicted),"recall":recall_score(truth,predicted),"f1":f1_score(truth,predicted)}

args = TrainingArguments(output_dir=str(OUTPUT_ROOT),seed=SEED,learning_rate=5e-5,num_train_epochs=5,per_device_train_batch_size=2,per_device_eval_batch_size=2,gradient_accumulation_steps=4,eval_strategy="epoch",save_strategy="epoch",load_best_model_at_end=True,metric_for_best_model="f1",greater_is_better=True,save_total_limit=2,report_to="none",fp16=torch.cuda.is_available())
trainer = Trainer(model=model,args=args,train_dataset=train_data,eval_dataset=validation_data,processing_class=processor,compute_metrics=compute_metrics)
trainer.train()
metrics = trainer.evaluate()
trainer.save_model(OUTPUT_ROOT/"best")
processor.save_pretrained(OUTPUT_ROOT/"best")
print(metrics)'''
        ),
        markdown("## 3. Khóa checkpoint và ghi report"),
        code(
            '''import hashlib
from datetime import datetime, timezone

def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()

payload = {
 "created_at":datetime.now(timezone.utc).isoformat(),
 "base_model":BASE_MODEL,"base_revision":BASE_REVISION,
 "split":"validation","test_used":False,"train_rows":len(train_data),"validation_rows":len(validation_data),
 "weak_alignment_policy":"exact normalized entity value to consecutive OCR words",
 "metrics":{key:float(value) for key,value in metrics.items() if isinstance(value,(int,float))},
 "checkpoint":str(OUTPUT_ROOT/"best"),"checkpoint_tree_sha256":tree_hash(OUTPUT_ROOT/"best"),"final_test_locked":True,
}
REPORT_PATH.parent.mkdir(parents=True,exist_ok=True)
REPORT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("Candidate report:",REPORT_PATH)
print("Final test locked: PASS")'''
        ),
    ]
    payload = {
        "cells": cells,
        "metadata": {"accelerator": "GPU", "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    main()
