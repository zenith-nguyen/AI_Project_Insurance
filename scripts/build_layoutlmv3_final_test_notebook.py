"""Build the guarded, one-time LayoutLMv3 SROIE final-test notebook."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_NOTEBOOK = ROOT / "notebooks/Document_LayoutLMv3_Candidate_Acc2_v3.ipynb"
OUTPUT = ROOT / "notebooks/Document_LayoutLMv3_Final_Test_Acc2_v1.ipynb"


def lines(value: str) -> list[str]:
    return [line + "\n" for line in value.strip("\n").split("\n")]


def markdown(value: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": lines(value)}


def code(value: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(value)}


def source(cell: dict) -> str:
    value = cell["source"]
    return "".join(value) if isinstance(value, list) else value


def candidate_fragments() -> tuple[str, str]:
    notebook = json.loads(CANDIDATE_NOTEBOOK.read_text(encoding="utf-8"))
    dataset_cell = next(source(cell) for cell in notebook["cells"] if "class SROIE(Dataset)" in source(cell))
    training_cell = next(source(cell) for cell in notebook["cells"] if "def compute_metrics(result):" in source(cell))
    definitions = dataset_cell.split("train_data = SROIE", 1)[0].rstrip()
    metrics = training_cell[training_cell.index("def bio_spans") : training_cell.index("args = TrainingArguments")].rstrip()
    metrics = metrics.replace("validation_metadata", "test_metadata")
    metrics = metrics.replace(
        'field_precision,field_recall,field_f1 = field_scores({"date","total"})',
        'field_precision,field_recall,field_f1 = field_scores({"date","total"})\n'
        '    date_precision,date_recall,date_f1 = field_scores({"date"})\n'
        '    total_precision,total_recall,total_f1 = field_scores({"total"})',
    )
    metrics = metrics.replace(
        '"field_micro_f1":field_f1,"all_field_micro_f1":all_f1}',
        '"field_micro_f1":field_f1,"date_precision":date_precision,"date_recall":date_recall,'
        '"date_f1":date_f1,"total_precision":total_precision,"total_recall":total_recall,'
        '"total_f1":total_f1,"all_field_micro_f1":all_f1}',
    )
    return definitions, metrics


def main() -> None:
    definitions, metrics = candidate_fragments()
    cells = [
        markdown(
            """# LayoutLMv3 SROIE — Final Test Acc 2 v1

Notebook này chỉ đánh giá **checkpoint đã được chọn trên validation**. Nó không train, không chọn lại epoch và không sửa threshold/alignment theo test. Test gồm 361 ảnh và chỉ được mở sau khi checkpoint hash, selection report và processed split đều hợp lệ. Execution lock ngăn chạy final test lần hai."""
        ),
        code(
            '''from pathlib import Path

PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
DATA_ROOT = PROJECT / "data/processed/documents/sroie/v1"
CANDIDATE_REPORT = PROJECT / "reports/metrics/documents/layoutlmv3_sroie_candidate_validation_v2.json"
SPLIT_REPORT = PROJECT / "reports/data_audit/documents/sroie_processed_split_v1.json"
FINAL_REPORT = PROJECT / "reports/metrics/documents/layoutlmv3_sroie_final_test_v1.json"
EXECUTION_LOCK = PROJECT / "reports/metrics/documents/layoutlmv3_sroie_final_test_v1.execution.json"
RUN_FINAL_TEST = True
EXPECTED_TEST_ROWS = 361
SEED = 20261012'''
        ),
        code(
            '''import subprocess, sys, importlib.util
requirements={"transformers":"transformers>=4.45,<6","accelerate":"accelerate>=1,<2","pyarrow":"pyarrow>=17,<26","PIL":"Pillow>=10,<13"}
for module,requirement in requirements.items():
    if importlib.util.find_spec(module) is None:
        subprocess.run([sys.executable,"-m","pip","install",requirement],check=True)
from google.colab import drive
drive.mount("/content/drive")

import hashlib, json, uuid
from datetime import datetime, timezone

def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def tree_hash(root):
    digest=hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()

if not RUN_FINAL_TEST: raise RuntimeError("RUN_FINAL_TEST chưa được mở.")
if FINAL_REPORT.exists(): raise FileExistsError(f"Final report đã tồn tại; không chạy lần hai: {FINAL_REPORT}")
if EXECUTION_LOCK.exists(): raise FileExistsError(f"Execution lock đã tồn tại; dừng để tránh đọc test lần hai: {EXECUTION_LOCK}")
selection=json.loads(CANDIDATE_REPORT.read_text(encoding="utf-8"))
split_report=json.loads(SPLIT_REPORT.read_text(encoding="utf-8"))
if not selection.get("candidate_selected"): raise RuntimeError("Candidate chưa được chọn theo locked rule.")
if not selection.get("final_test_locked") or selection.get("test_used"): raise RuntimeError("Selection protocol không hợp lệ.")
if not split_report.get("valid") or any(split_report["cross_split_exact_duplicates"].values()): raise RuntimeError("Processed split chưa sạch.")
CHECKPOINT=Path(selection["checkpoint"])
if not CHECKPOINT.is_dir(): raise FileNotFoundError(f"Thiếu checkpoint: {CHECKPOINT}")
checkpoint_hash=tree_hash(CHECKPOINT)
if checkpoint_hash != selection["checkpoint_tree_sha256"]: raise RuntimeError("Checkpoint tree hash không khớp selection report.")
run_id=uuid.uuid4().hex
execution={"run_id":run_id,"status":"started","test_run_number":1,"started_at":datetime.now(timezone.utc).isoformat(),"checkpoint_tree_sha256":checkpoint_hash,"selection_report_sha256":sha256_file(CANDIDATE_REPORT)}
EXECUTION_LOCK.parent.mkdir(parents=True,exist_ok=True)
EXECUTION_LOCK.write_text(json.dumps(execution,ensure_ascii=False,indent=2),encoding="utf-8")
print("Model/checkpoint/split lock: PASS")
print("Execution lock created:",EXECUTION_LOCK)'''
        ),
        markdown("## Định nghĩa dataset và metric đã khóa từ candidate"),
        code(definitions),
        markdown("## Mở test và đánh giá đúng một lần"),
        code(
            f'''test_data = SROIE(DATA_ROOT/"test.parquet")
if len(test_data) != EXPECTED_TEST_ROWS: raise RuntimeError(f"Unexpected test rows: {{len(test_data)}}")
test_metadata = test_data.evaluation_metadata()
print("Final test rows:",len(test_data))

{metrics}

model = LayoutLMv3ForTokenClassification.from_pretrained(CHECKPOINT)
args = TrainingArguments(output_dir="/content/layoutlmv3_final_test_runtime",seed=SEED,per_device_eval_batch_size=2,report_to="none",fp16=torch.cuda.is_available())
trainer = Trainer(model=model,args=args,eval_dataset=test_data,processing_class=processor,compute_metrics=compute_metrics)
metrics = trainer.evaluate()
print(metrics)'''
        ),
        markdown("## Ghi final report và đóng execution lock"),
        code(
            '''report={
 "created_at":datetime.now(timezone.utc).isoformat(),
 "run_id":run_id,"test_run_number":1,"split":"test","test_rows":len(test_data),
 "selected_checkpoint":str(CHECKPOINT),"checkpoint_tree_sha256":checkpoint_hash,
 "selection_report":str(CANDIDATE_REPORT),"selection_report_sha256":sha256_file(CANDIDATE_REPORT),
 "test_used_for_selection":False,
 "metrics":{key:float(value) for key,value in metrics.items() if isinstance(value,(int,float))},
 "scope":{"fields":["date","total"],"dataset":"SROIE processed v1"},
 "limitations":["Public receipt data is not Vietnamese insurance-domain validation.","Only date and total are evaluated."],
}
FINAL_REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
execution.update({"status":"completed","completed_at":datetime.now(timezone.utc).isoformat(),"final_report":str(FINAL_REPORT),"final_report_sha256":sha256_file(FINAL_REPORT)})
EXECUTION_LOCK.write_text(json.dumps(execution,ensure_ascii=False,indent=2),encoding="utf-8")
print("=== LAYOUTLMV3 FINAL TEST: PASS ===")
print("Field micro-F1:",report["metrics"].get("eval_field_micro_f1"))
print("Date F1:",report["metrics"].get("eval_date_f1"))
print("Total F1:",report["metrics"].get("eval_total_f1"))
print("Final report:",FINAL_REPORT)
print("Không chạy lại final test.")'''
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
