"""Evaluate aligned B0-B5 prediction columns and create Phase 5 evidence."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, precision_recall_curve

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluation.metrics import evaluate, paired_stratified_bootstrap, precision_at_k, recall_at_k


def _load_predictions(path: Path, config: dict) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    frame = pd.read_csv(path)
    id_column, label_column = config["id_column"], config["label_column"]
    for column in (id_column, label_column):
        if column not in frame:
            raise ValueError(f"Missing required column: {column}")
    if frame[id_column].isna().any() or not frame[id_column].is_unique:
        raise ValueError("claim_id values must be unique and non-null")
    labels = frame[label_column].to_numpy()
    if not set(np.unique(labels)).issubset({0, 1}) or len(np.unique(labels)) != 2:
        raise ValueError("fraud_label must contain both binary classes 0 and 1")
    scores = {}
    for stage, spec in config["stages"].items():
        column = spec["score_column"]
        if column not in frame or frame[column].isna().all():
            continue
        if frame[column].isna().any():
            raise ValueError(f"{column} is partially missing; every evaluated stage must score the same claims")
        values = frame[column].astype(float).to_numpy()
        if not np.isfinite(values).all():
            raise ValueError(f"{column} contains non-finite scores")
        scores[stage] = values
    if not scores:
        raise ValueError("No complete B0-B5 score column was found")
    return frame, scores


def _plot_pr(labels: np.ndarray, scores: dict[str, np.ndarray], config: dict, target: Path) -> None:
    fig, axis = plt.subplots(figsize=(8, 5.2))
    for stage, values in scores.items():
        precision, recall, _ = precision_recall_curve(labels, values)
        ap = average_precision_score(labels, values)
        axis.plot(recall, precision, linewidth=2, label=f"{stage} · AP={ap:.3f}")
    axis.axhline(labels.mean(), color="#8a9799", linestyle="--", linewidth=1, label=f"Prevalence={labels.mean():.3f}")
    axis.set(xlabel="Recall", ylabel="Precision", title="Phase 5 · Precision–Recall curves")
    axis.set_xlim(0, 1); axis.set_ylim(0, 1.02); axis.grid(alpha=.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig)


def _plot_at_k(labels: np.ndarray, scores: dict[str, np.ndarray], config: dict, target: Path) -> None:
    k_values = [float(value) for value in config["k_values"]]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharex=True)
    for stage, values in scores.items():
        axes[0].plot([k * 100 for k in k_values], [recall_at_k(labels, values, k) for k in k_values], marker="o", label=stage)
        axes[1].plot([k * 100 for k in k_values], [precision_at_k(labels, values, k) for k in k_values], marker="o", label=stage)
    axes[0].set_title("Recall@K"); axes[1].set_title("Precision@K")
    for axis in axes:
        axis.set_xlabel("Tỷ lệ hàng đợi K (%)"); axis.set_ylim(0, 1.02); axis.grid(alpha=.2)
    axes[0].set_ylabel("Metric"); axes[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig)


def _markdown(report: dict, config: dict) -> str:
    lines = [
        "# Phase 5 — Baseline & Evaluation Report",
        "",
        f"**Generated:** {report['created_at']}  ",
        f"**Dataset:** {report['dataset']['name']}  ",
        f"**Rows:** {report['dataset']['rows']} · positives: {report['dataset']['positives']} · prevalence: {report['dataset']['prevalence']:.3f}",
        "",
        "> Average Precision (AP) là primary ranking metric của dự án. Mọi B-stage trong một so sánh phải chấm đúng cùng claim theo cùng thứ tự.",
        "",
        "## Kết quả theo baseline",
        "",
        "| Stage | Trạng thái | AP | Recall@10% | Precision@10% | Ghi chú |",
        "|---|---|---:|---:|---:|---|",
    ]
    for stage, spec in config["stages"].items():
        metric = report["stages"].get(stage)
        if metric:
            lines.append(f"| {stage} · {spec['title']} | evaluated | {metric['average_precision']:.4f} | {metric['recall_at_10pct']:.4f} | {metric['precision_at_10pct']:.4f} | {spec['definition']} |")
        else:
            lines.append(f"| {stage} · {spec['title']} | not evaluated | — | — | — | {spec['current_data_status']} |")
    lines += ["", "## Paired bootstrap 1.000 lần", "", "| So sánh | Metric | Hiệu số | CI 95% | Chứa 0? | Kết luận |", "|---|---|---:|---:|---|---|"]
    for name, comparison in report["comparisons"].items():
        if comparison["status"] != "evaluated":
            lines.append(f"| {name} | — | — | — | — | {comparison['reason']} |")
            continue
        for metric, values in comparison["metrics"].items():
            conclusion = "Chưa đủ bằng chứng khác biệt" if values["contains_zero"] else ("Candidate tốt hơn" if values["delta"] > 0 else "Candidate kém hơn")
            lines.append(f"| {name} | {metric} | {values['delta']:.4f} | [{values['lower']:.4f}; {values['upper']:.4f}] | {'Có' if values['contains_zero'] else 'Không'} | {conclusion} |")
    lines += [
        "", "## Biểu đồ", "", "![PR curves](phase5_pr_curves.png)", "", "![Recall và Precision tại K](phase5_at_k.png)",
        "", "## Giới hạn bắt buộc", "",
        f"- {config['data_policy']['forbidden_join']}",
        f"- Final requirement: {config['data_policy']['final_requirement']}",
        "- CI không chứa 0 chỉ là bằng chứng thống kê có điều kiện trên sample; vẫn phải kiểm tra domain shift, leakage, calibration và chi phí nghiệp vụ.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path, help="Wide CSV: claim_id,fraud_label,B0_score,...,B5_score")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase5_evaluation.v1.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/phase5")
    parser.add_argument("--dataset-name", default="unspecified_aligned_claim_set")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    frame, scores = _load_predictions(args.predictions, config)
    labels = frame[config["label_column"]].astype(int).to_numpy()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    stage_metrics = {stage: evaluate(labels, values, tuple(config["k_values"])) for stage, values in scores.items()}
    comparisons = {}
    for item in config["comparisons"]:
        baseline, candidate = item["baseline"], item["candidate"]
        if baseline not in scores or candidate not in scores:
            comparisons[item["name"]] = {"status": "not_evaluated", "reason": f"Missing aligned scores for {baseline} or {candidate}"}
            continue
        comparisons[item["name"]] = {
            "status": "evaluated",
            "baseline": baseline,
            "candidate": candidate,
            "metrics": paired_stratified_bootstrap(labels, scores[baseline], scores[candidate], 0.10, int(config["bootstrap"]["samples"]), int(config["bootstrap"]["seed"])),
        }
    report = {
        "schema_version": "phase5_evaluation_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {"name": args.dataset_name, "rows": len(frame), "positives": int(labels.sum()), "prevalence": float(labels.mean())},
        "evaluated_stages": list(scores),
        "stages": stage_metrics,
        "comparisons": comparisons,
        "data_policy": config["data_policy"],
    }
    _plot_pr(labels, scores, config, output / "phase5_pr_curves.png")
    _plot_at_k(labels, scores, config, output / "phase5_at_k.png")
    (output / "phase5_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "PHASE5_EVALUATION_REPORT.md").write_text(_markdown(report, config), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evaluated_stages": list(scores), "output_dir": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
