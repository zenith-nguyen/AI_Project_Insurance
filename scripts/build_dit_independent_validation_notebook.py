"""Build an independent RVL-CDIP validation benchmark for the pinned DiT model."""
from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("notebooks/Document_DiT_Independent_Validation_Acc2_v1.ipynb")


def cell(kind: str, value: str) -> dict:
    payload = {"cell_type": kind, "metadata": {}, "source": [line + "\n" for line in value.strip("\n").split("\n")]}
    if kind == "code":
        payload.update(execution_count=None, outputs=[])
    return payload


def main() -> None:
    cells = [
        cell("markdown", """# DiT Independent RVL-CDIP Validation — Acc 2 v1

Notebook sửa giới hạn của baseline v1: sample intake ban đầu được lấy từ upstream `train`. Bản này lấy 20 ảnh mỗi lớp trực tiếp từ upstream `validation`, không dùng để train hay chọn threshold, rồi đánh giá checkpoint DiT đã pin."""),
        cell("code", '''from pathlib import Path
PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
RVL_ROOT = PROJECT / "data/bronze/documents/rvl_cdip/mirror_main"
LOADER = RVL_ROOT / "loader_compat/rvl_cdip.py"
REPORT = PROJECT / "reports/metrics/documents/dit_rvl_official_validation_v1.json"
MODEL_ID = "microsoft/dit-base-finetuned-rvlcdip"
REVISION = "23f8b03d130fb66bbc9a15df3c75d753e49240eb"
SEED = 20261011
SAMPLES_PER_CLASS = 20
RUN_FINAL_TEST = False'''),
        cell("code", '''import importlib.util, subprocess, sys
requirements={"datasets":"datasets==3.6.0","transformers":"transformers>=4.45,<6","sklearn":"scikit-learn>=1.5,<2"}
for module,requirement in requirements.items():
    if importlib.util.find_spec(module) is None:
        subprocess.run([sys.executable,"-m","pip","install",requirement],check=True)
from google.colab import drive
drive.mount("/content/drive")
if not LOADER.is_file(): raise FileNotFoundError(f"Thiếu compatibility loader: {LOADER}")
if RUN_FINAL_TEST: raise RuntimeError("Notebook này chỉ chạy validation.")
print("Environment: PASS")'''),
        cell("code", '''from collections import Counter
import json
from datetime import datetime, timezone
import torch
from datasets import load_dataset
from sklearn.metrics import balanced_accuracy_score, classification_report, f1_score
from transformers import AutoImageProcessor, AutoModelForImageClassification

stream=load_dataset(str(LOADER),split="validation",streaming=True,trust_remote_code=True).shuffle(seed=SEED,buffer_size=5000)
label_names=stream.features["label"].names
counts=Counter(); rows=[]
for example in stream:
    label=int(example["label"])
    if counts[label]>=SAMPLES_PER_CLASS: continue
    rows.append({"image":example["image"].convert("RGB"),"label":label})
    counts[label]+=1
    if len(counts)==16 and set(counts.values())=={SAMPLES_PER_CLASS}: break
if len(rows)!=16*SAMPLES_PER_CLASS: raise RuntimeError(f"Validation sample incomplete: {counts}")
print("Official validation sample:",{label_names[k]:v for k,v in sorted(counts.items())})

processor=AutoImageProcessor.from_pretrained(MODEL_ID,revision=REVISION)
model=AutoModelForImageClassification.from_pretrained(MODEL_ID,revision=REVISION).to("cuda" if torch.cuda.is_available() else "cpu").eval()
truth=[]; predicted=[]
for start in range(0,len(rows),16):
    batch=rows[start:start+16]
    inputs={k:v.to(model.device) for k,v in processor(images=[row["image"] for row in batch],return_tensors="pt").items()}
    with torch.inference_mode(): ids=model(**inputs).logits.argmax(-1).cpu().tolist()
    truth.extend(label_names[row["label"]] for row in batch)
    predicted.extend(model.config.id2label[index] for index in ids)

payload={"created_at":datetime.now(timezone.utc).isoformat(),"model":MODEL_ID,"revision":REVISION,"source_split":"validation","sample_seed":SEED,"samples_per_class":SAMPLES_PER_CLASS,"validation_rows":len(rows),"test_used":False,"macro_f1":f1_score(truth,predicted,average="macro"),"balanced_accuracy":balanced_accuracy_score(truth,predicted),"classification_report":classification_report(truth,predicted,output_dict=True,zero_division=0)}
REPORT.parent.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("Independent macro-F1:",payload["macro_f1"])
print("Independent balanced accuracy:",payload["balanced_accuracy"])
print("Report:",REPORT)'''),
    ]
    payload={"cells":cells,"metadata":{"accelerator":"GPU","kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"nbformat":4,"nbformat_minor":5}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    main()
