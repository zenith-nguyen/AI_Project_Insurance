"""Run as one Colab cell after the locked final inference hit metric_value NameError.

This deliberately recovers the EvalPrediction object from the live traceback.
It does not call Trainer.evaluate/predict and does not read test.parquet again.
"""
import json
import sys
from datetime import datetime, timezone


if FINAL_REPORT.exists():
    raise FileExistsError(f"Final report already exists: {FINAL_REPORT}")

locked_execution = json.loads(EXECUTION_LOCK.read_text(encoding="utf-8"))
if locked_execution.get("run_id") != run_id:
    raise RuntimeError("In-memory run_id does not match execution lock.")
if locked_execution.get("status") != "test_access_started":
    raise RuntimeError(f"Unexpected execution state: {locked_execution.get('status')}")

traceback_object = getattr(sys, "last_traceback", None)
if traceback_object is None:
    shell = get_ipython()  # noqa: F821 - available in Colab
    last_result = getattr(shell, "last_execution_result", None)
    last_error = getattr(last_result, "error_in_exec", None)
    traceback_object = getattr(last_error, "__traceback__", None)

eval_prediction = None
while traceback_object is not None:
    frame = traceback_object.tb_frame
    if frame.f_code.co_name == "compute_metrics" and "result" in frame.f_locals:
        eval_prediction = frame.f_locals["result"]
        break
    traceback_object = traceback_object.tb_next

if eval_prediction is None:
    raise RuntimeError(
        "Cannot recover EvalPrediction from RAM. Stop here; do not rerun inference."
    )
if len(eval_prediction.label_ids) != EXPECTED_TEST_ROWS:
    raise RuntimeError(
        f"Recovered rows mismatch: {len(eval_prediction.label_ids)} != {EXPECTED_TEST_ROWS}"
    )


def metric_value(field, value):
    if field == "date" and parsed_dates(value):
        return min(parsed_dates(value)).isoformat()
    if field == "total" and parsed_amounts(value):
        return str(min(parsed_amounts(value)).normalize())
    return normalize(value)


recovered_metrics = compute_metrics(eval_prediction)
metrics = {f"eval_{key}": float(value) for key, value in recovered_metrics.items()}
required_metrics = {"eval_field_micro_f1", "eval_date_f1", "eval_total_f1"}
if not required_metrics.issubset(metrics):
    raise RuntimeError(f"Missing recovered metrics: {required_metrics - set(metrics)}")
if any(not 0.0 <= metrics[key] <= 1.0 for key in required_metrics):
    raise RuntimeError(f"Metric outside [0, 1]: {metrics}")

report = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "run_id": run_id,
    "test_run_number": 1,
    "split": "test",
    "test_rows": EXPECTED_TEST_ROWS,
    "selected_checkpoint": str(CHECKPOINT),
    "checkpoint_tree_sha256": checkpoint_hash,
    "selection_report": str(CANDIDATE_REPORT),
    "selection_report_sha256": sha256_file(CANDIDATE_REPORT),
    "test_used_for_selection": False,
    "metrics": metrics,
    "scope": {"fields": ["date", "total"], "dataset": "SROIE processed v1"},
    "recovery": {
        "reason": "metric_value NameError after the single inference pass",
        "source": "EvalPrediction recovered from the live traceback",
        "inference_repeated": False,
        "test_reread": False,
    },
    "limitations": [
        "Public receipt data is not Vietnamese insurance-domain validation.",
        "Only date and total are evaluated.",
    ],
}
FINAL_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

locked_execution.update(
    {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "metric_recovery": report["recovery"],
        "final_report": str(FINAL_REPORT),
        "final_report_sha256": sha256_file(FINAL_REPORT),
    }
)
EXECUTION_LOCK.write_text(
    json.dumps(locked_execution, ensure_ascii=False, indent=2), encoding="utf-8"
)

print("=== LAYOUTLMV3 FINAL TEST RECOVERY: PASS ===")
print("Inference repeated: False")
print("Test reread: False")
print("Rows:", EXPECTED_TEST_ROWS)
print("Field micro-F1:", metrics["eval_field_micro_f1"])
print("Date F1:", metrics["eval_date_f1"])
print("Total F1:", metrics["eval_total_f1"])
print("Final report:", FINAL_REPORT)
print("Execution lock:", EXECUTION_LOCK)
