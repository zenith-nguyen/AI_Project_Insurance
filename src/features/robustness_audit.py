"""Train-only ablation of social proxies and uncertain post-claim fields."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold

from src.data.common import ROOT, config, utc_now, write_json
from src.evaluation.metrics import evaluate
from src.features.preprocessing import features
from src.models.train import _pipeline


def evaluate_profile(x: pd.DataFrame, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]], seed: int) -> dict:
    scores = []
    for train_idx, holdout_idx in splits:
        model = _pipeline("xgboost", x, seed)
        model.fit(x.iloc[train_idx], y[train_idx])
        predicted = model.predict_proba(x.iloc[holdout_idx])[:, 1]
        scores.append(evaluate(y[holdout_idx], predicted, (0.1,)))
    return {
        "average_precision_mean": float(np.mean([row["average_precision"] for row in scores])),
        "average_precision_std_across_folds": float(np.std([row["average_precision"] for row in scores], ddof=1)),
        "recall_at_10pct_mean": float(np.mean([row["recall_at_10pct"] for row in scores])),
        "recall_at_10pct_std_across_folds": float(np.std([row["recall_at_10pct"] for row in scores], ddof=1)),
        "fold_count": len(scores),
        "feature_count_before_encoding": len(x.columns),
        "features": list(x.columns),
    }


def run() -> dict:
    params = config("params.yaml")
    stages = config("configs/stages.yaml")
    train_path = ROOT / "data/gold" / params["gold"]["version"] / "train.parquet"
    train = pd.read_parquet(train_path)
    x = features(train)
    y = train.fraud_label.astype(int).to_numpy()
    folds = list(RepeatedStratifiedKFold(n_splits=params["cv"]["n_splits"], n_repeats=params["cv"]["n_repeats"], random_state=params["seed"]).split(x, y))
    profiles = {}
    for name, stage in stages.items():
        missing = sorted(set(stage["features"]) - set(x.columns))
        if missing:
            raise ValueError(f"Missing {name} feature columns: {missing}")
        profiles[name] = x[stage["features"]]
    result = {"created_at_utc": utc_now(), "gold_version": params["gold"]["version"], "protocol": "XGBoost repeated stratified CV on train only; same 25 folds as model selection", "profiles": {name: evaluate_profile(profile, y, folds, params["seed"]) for name, profile in profiles.items()}}
    write_json(ROOT / "reports/metrics/robustness_v1.json", result)
    original = json.loads((ROOT / "reports/metrics/tabular_v1.json").read_text(encoding="utf-8"))["cv"]["xgboost"]
    hobby = pd.crosstab(train.insured_hobbies, train.fraud_label)
    selected_hobbies = [name for name in ("cross-fit", "chess") if name in hobby.index]
    lines = ["# Kiểm tra độ nhạy theo nhóm feature", "", "Đây là phân tích thăm dò bằng CV chỉ trên train; không dùng nhãn validation/test và không thay đổi kết quả test đã chốt.", "", "| Nhóm feature | Average Precision CV trung bình | Recall@10% CV trung bình | Số cột đầu vào |", "|---|---:|---:|---:|", f"| Mô hình nghiên cứu hiện tại | {original['average_precision']:.3f} | {original['recall_at_10pct']:.3f} | {len(x.columns)} |"]
    for name, report in result["profiles"].items():
        lines.append(f"| {name} | {report['average_precision_mean']:.3f} | {report['recall_at_10pct_mean']:.3f} | {report['feature_count_before_encoding']} |")
    lines += ["", "SHAP của mô hình hiện tại bị chi phối bởi nhóm sở thích. Số lượng trên train dưới đây cho thấy cần kiểm tra nguồn gốc tín hiệu; đây không phải quan hệ nhân quả:", ""]
    for name in selected_hobbies:
        negative, positive = int(hobby.loc[name, 0]), int(hobby.loc[name, 1])
        lines.append(f"- `{name}`: {positive} nhãn fraud và {negative} nhãn non-fraud trong {positive + negative} dòng train.")
    lines += ["", "`stage1_intake` chỉ dùng thông tin hợp đồng/xe và sự cố cơ bản. `stage3_complete` thêm thông tin từ hồ sơ đã hoàn chỉnh nhưng bỏ sở thích, nhân khẩu học, nghề nghiệp, vốn và địa lý. Nhóm vẫn phải xác nhận từng trường có sẵn tại thời điểm chấm điểm hay không.", "", "Kết luận: giữ mô hình ban đầu làm baseline nghiên cứu. Hai nhóm theo giai đoạn là ứng viên thăm dò, chưa đủ cơ sở để ra quyết định tự động. Cần xác nhận thời điểm có dữ liệu, nguồn gốc nhãn và ảnh hưởng theo nhóm khách hàng."]
    (ROOT / "reports/ROBUSTNESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run()["profiles"], indent=2))
