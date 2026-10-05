"""Evaluate candidate feature policies on val_fs without reading the spent test."""
from __future__ import annotations

import json

import pandas as pd

from src.data.common import ROOT, config, sha256, utc_now, write_json
from src.evaluation.metrics import evaluate
from src.features.preprocessing import features
from src.models.train import _pipeline


def _load_feature_selection_splits() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    params = config("params.yaml")
    folder = ROOT / "data/gold" / params["feature_selection"]["version"]
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    frames = {}
    for name in ("train_fs", "val_fs"):
        path = folder / f"{name}.parquet"
        if sha256(path) != manifest["splits"][name]["sha256"]:
            raise ValueError(f"{name} hash mismatch")
        frames[name] = pd.read_parquet(path)
    if set(frames["train_fs"].claim_id) & set(frames["val_fs"].claim_id):
        raise ValueError("claim_id overlap between train_fs and val_fs")
    return frames["train_fs"], frames["val_fs"], manifest


def run() -> dict:
    params = config("params.yaml")
    stages = config("configs/stages.yaml")
    train, validation, manifest = _load_feature_selection_splits()
    y_train = train.fraud_label.astype(int).to_numpy()
    y_validation = validation.fraud_label.astype(int).to_numpy()

    full_train = features(train, exclude_biased_features=False)
    full_validation = features(validation, exclude_biased_features=False)
    bias_train = features(train, exclude_biased_features=True)
    bias_validation = features(validation, exclude_biased_features=True)
    profiles = {
        "research_full": (full_train, full_validation),
        "bias_excluded_current": (bias_train, bias_validation),
    }
    for name, stage in stages.items():
        missing = sorted(set(stage["features"]) - set(bias_train.columns))
        if missing:
            raise ValueError(f"Missing {name} feature columns: {missing}")
        profiles[name] = (bias_train[stage["features"]], bias_validation[stage["features"]])

    results = {}
    for name, (x_train, x_validation) in profiles.items():
        if list(x_train.columns) != list(x_validation.columns):
            raise ValueError(f"Feature schema mismatch for {name}")
        model = _pipeline("xgboost", x_train, params["seed"])
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_validation)[:, 1]
        results[name] = {
            "feature_count_before_encoding": len(x_train.columns),
            "features": list(x_train.columns),
            **evaluate(y_validation, scores, params["evaluation"]["k_values"]),
        }

    result = {
        "created_at_utc": utc_now(),
        "protocol": "Fixed XGBoost fit on train_fs and evaluated on val_fs; original 200-row test was not read",
        "split_version": manifest["version"],
        "train_fs_sha256": manifest["splits"]["train_fs"]["sha256"],
        "val_fs_sha256": manifest["splits"]["val_fs"]["sha256"],
        "original_frozen_test_status": manifest["original_frozen_test_status"],
        "profiles": results,
        "limitations": [
            "val_fs has only 140 rows and is for feature-policy decisions, not final performance claims",
            "stage feature availability still requires business confirmation",
            "an external final test is still required after policy and model choices are frozen",
        ],
    }
    write_json(ROOT / "reports/metrics/feature_policy_val_fs_v1.json", result)

    pct = lambda value: f"{100 * value:.1f}%"
    lines = [
        "# Feature-policy validation trên `val_fs`",
        "",
        "Mỗi profile dùng cùng cấu hình XGBoost, fit trên `train_fs` và đánh giá trên `val_fs`. Script không đọc test 200 dòng đã dùng hai lần trước đó. Đây là bằng chứng để chọn feature, không phải ước lượng hiệu năng cuối cùng.",
        "",
        "| Profile | Số feature | AP | ROC-AUC | Recall@10% | Recall@20% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in results.items():
        lines.append(
            f"| `{name}` | {metrics['feature_count_before_encoding']} | {metrics['average_precision']:.3f} | "
            f"{metrics['roc_auc']:.3f} | {pct(metrics['recall_at_10pct'])} | {pct(metrics['recall_at_20pct'])} |"
        )
    lines += [
        "",
        "`research_full` giữ nhóm proxy để làm mốc nghiên cứu; `bias_excluded_current` bỏ `insured_hobbies`, `insured_zip` và `incident_location`; hai profile theo stage vẫn là ứng viên cho đến khi nghiệp vụ xác nhận thời điểm có sẵn của từng trường.",
        "",
        "Không dùng bảng này để tuyên bố production readiness. Sau khi chốt feature policy và model, cần một external test mới cho đánh giá cuối cùng.",
    ]
    (ROOT / "reports/FEATURE_POLICY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run()["profiles"], ensure_ascii=False, indent=2))
