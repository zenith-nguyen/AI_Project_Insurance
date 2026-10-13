"""Build the one-time LayoutLMv3 final-test recovery notebook.

This notebook is only for the specific state where the v3 final-test notebook
created its execution record but stopped before the test-loading cell ran.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "notebooks" / "Document_LayoutLMv3_Final_Test_Acc2_v3.ipynb"
OUTPUT = ROOT / "notebooks" / "Document_LayoutLMv3_Final_Test_Recovery_Acc2_v1.ipynb"


def set_source(cell: dict, source: str) -> None:
    cell["source"] = source.splitlines(keepends=True)


def main() -> None:
    notebook = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    set_source(
        notebook["cells"][0],
        """# LayoutLMv3 SROIE — Final Test Recovery Acc 2 v1

Notebook này chỉ tiếp tục execution record đã được v3 tạo nhưng đã dừng **trước cell đọc test**. Nó không tạo run mới. Recovery sẽ bị chặn nếu final report đã tồn tại, execution không ở trạng thái `started`, hoặc lock đã có `test_access_started_at`.

Đây là recovery một lần cho sự cố tải processor ngày 13/10/2026. Không dùng notebook này cho một final-test run khác.
""",
    )

    lock_cell = next(
        cell
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "Execution lock created:" in "".join(cell.get("source", []))
    )
    original = "".join(lock_cell["source"])
    start = original.index('if not RUN_FINAL_TEST:')
    replacement = '''if not RUN_FINAL_TEST: raise RuntimeError("RUN_FINAL_TEST chưa được mở.")
if FINAL_REPORT.exists(): raise FileExistsError(f"Final report đã tồn tại; không recovery: {FINAL_REPORT}")
if not EXECUTION_LOCK.exists(): raise FileNotFoundError(f"Không có execution lock để recovery: {EXECUTION_LOCK}")

selection=json.loads(CANDIDATE_REPORT.read_text(encoding="utf-8"))
split_report=json.loads(SPLIT_REPORT.read_text(encoding="utf-8"))
execution=json.loads(EXECUTION_LOCK.read_text(encoding="utf-8"))
if not selection.get("candidate_selected"): raise RuntimeError("Candidate chưa được chọn theo locked rule.")
if not selection.get("final_test_locked") or selection.get("test_used"): raise RuntimeError("Selection protocol không hợp lệ.")
if not split_report.get("valid") or any(split_report["cross_split_exact_duplicates"].values()): raise RuntimeError("Processed split chưa sạch.")
if execution.get("status") != "started" or execution.get("test_run_number") != 1: raise RuntimeError(f"Execution state không recovery được: {execution}")
if execution.get("test_access_started_at"): raise RuntimeError("Lock cho biết test access đã bắt đầu; không được đọc test lại.")

reported_checkpoint=Path(selection["checkpoint"])
CHECKPOINT=reported_checkpoint if reported_checkpoint.is_dir() else PROJECT/CHECKPOINT_REL
if not CHECKPOINT.is_dir(): raise FileNotFoundError(f"Thiếu checkpoint: {CHECKPOINT}")
checkpoint_hash=tree_hash(CHECKPOINT)
selection_hash=sha256_file(CANDIDATE_REPORT)
if checkpoint_hash != selection["checkpoint_tree_sha256"]: raise RuntimeError("Checkpoint tree hash không khớp selection report.")
if checkpoint_hash != execution.get("checkpoint_tree_sha256"): raise RuntimeError("Checkpoint tree hash không khớp execution lock.")
if selection_hash != execution.get("selection_report_sha256"): raise RuntimeError("Selection report hash không khớp execution lock.")
run_id=execution["run_id"]
print("Recovery gate: PASS")
print("Reusing run_id:",run_id)
print("Test access recorded previously: False")
'''
    set_source(lock_cell, original[:start] + replacement)

    evaluation_cell = next(
        cell
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and 'test_data = SROIE(DATA_ROOT/"test.parquet")' in "".join(cell.get("source", []))
    )
    evaluation = "".join(evaluation_cell["source"])
    marker = '''# Atomic audit marker: from this line onward the locked test is considered opened.
execution.update({
    "status":"test_access_started",
    "test_access_started_at":datetime.now(timezone.utc).isoformat(),
    "recovery_notebook":"Document_LayoutLMv3_Final_Test_Recovery_Acc2_v1.ipynb",
})
EXECUTION_LOCK.write_text(json.dumps(execution,ensure_ascii=False,indent=2),encoding="utf-8")
print("Test-access marker written. Do not rerun if execution stops after this line.")

'''
    set_source(evaluation_cell, marker + evaluation)

    for cell in notebook["cells"]:
        if cell.get("cell_type") == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
