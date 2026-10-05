"""Render reproducible, human-readable experiment results."""
from __future__ import annotations

import json

from src.data.common import ROOT


def render() -> str:
    result = json.loads((ROOT / "reports/metrics/tabular_v1.json").read_text(encoding="utf-8"))
    bias_file = ROOT / "reports/metrics/tabular_bias_excluded_v1.json"
    bias_result = json.loads(bias_file.read_text(encoding="utf-8")) if bias_file.exists() else None
    test, rule, intervals = result["test"], result["rule_baseline_test"], result["test_ci_95"]
    ops = result["test_operations"]
    robustness_file = ROOT / "reports/metrics/robustness_v1.json"
    robustness = json.loads(robustness_file.read_text(encoding="utf-8")) if robustness_file.exists() else None
    pct = lambda value: f"{100 * value:.1f}%"
    lines = [
        "# Kết quả nhánh tabular v1", "",
        f"Nguồn: Kaggle insurance-fraud-detection; Gold `{result['gold_version']}`. Tập test có {test['n']} hồ sơ, {test['fraud_count']} nhãn fraud ({pct(test['prevalence'])}).",
        "", "## So sánh trên frozen test", "",
        "| Chỉ số | Mô hình được chọn | Rule baseline |", "|---|---:|---:|",
        f"| Average Precision | {test['average_precision']:.3f} | {rule['average_precision']:.3f} |",
        f"| ROC-AUC | {test['roc_auc']:.3f} | {rule['roc_auc']:.3f} |",
        f"| Recall@10% | {pct(test['recall_at_10pct'])} | {pct(rule['recall_at_10pct'])} |",
        f"| Precision@10% | {pct(test['precision_at_10pct'])} | {pct(rule['precision_at_10pct'])} |",
        "", f"Mô hình `{result['selected_model']}` được chọn bằng Average Precision trung bình của repeated stratified CV trên train. Chênh lệch Recall@10% so với rule là {100 * (test['recall_at_10pct'] - rule['recall_at_10pct']):.1f} điểm phần trăm; chưa đạt mục tiêu đề xuất +10 điểm phần trăm.",
        "", "## Độ bất định và vận hành", "",
        f"Khoảng tin cậy bootstrap phân tầng 95% cho Recall@10%: {pct(intervals['recall_at_k']['lower'])}–{pct(intervals['recall_at_k']['upper'])}; cho Average Precision: {intervals['average_precision']['lower']:.3f}–{intervals['average_precision']['upper']:.3f}. Đây là khoảng tin cậy có điều kiện trên tập test nhỏ, không phản ánh shift dữ liệu.",
        f"Brier score: {test['brier']:.3f}; ECE 10 bins: {test['ece_10_bins']:.3f}. Điểm xác suất được hiệu chỉnh trên dữ liệu train có tỷ lệ fraud 24,7%; chưa được xác thực như xác suất fraud tại production.",
        f"Ngưỡng từ validation tạo tổng hàng đợi review {pct(ops['total_review_rate'])} trên test (mục tiêu validation 10%); SIU {pct(ops['siu_rate'])}, STP candidate {pct(ops['stp_rate'])}, false hold {pct(ops['false_hold_rate'])}. Hàng đợi thay đổi khi phân bố dữ liệu đổi.",
    ]
    if bias_result:
        bias = bias_result["test"]
        lines.extend([
            "", "## Chi phí của việc loại các feature có nguy cơ bias", "",
            "Cấu hình `EXCLUDE_BIASED_FEATURES: true` loại `insured_hobbies`, `insured_zip` và `incident_location`. Hai cột sau vốn đã thuộc danh sách loại trừ; thay đổi thực tế so với baseline v1 là loại thêm `insured_hobbies`. Biến thể được chọn lại mô hình bằng cùng protocol CV trên train và đánh giá trên cùng frozen test.", "",
            "| Chỉ số | Baseline v1 | Loại biased features | Thay đổi |", "|---|---:|---:|---:|",
            f"| Average Precision | {test['average_precision']:.3f} | {bias['average_precision']:.3f} | {bias['average_precision'] - test['average_precision']:+.3f} |",
            f"| ROC-AUC | {test['roc_auc']:.3f} | {bias['roc_auc']:.3f} | {bias['roc_auc'] - test['roc_auc']:+.3f} |",
            f"| Recall@10% | {pct(test['recall_at_10pct'])} | {pct(bias['recall_at_10pct'])} | {100 * (bias['recall_at_10pct'] - test['recall_at_10pct']):+.1f} điểm % |",
            f"| Recall@20% | {pct(test['recall_at_20pct'])} | {pct(bias['recall_at_20pct'])} | {100 * (bias['recall_at_20pct'] - test['recall_at_20pct']):+.1f} điểm % |",
            "", "Việc so sánh nhiều biến thể trên cùng test khiến test không còn hoàn toàn untouched cho các quyết định tiếp theo. Kết quả này được xem là sensitivity analysis đã định trước; cần một external test mới để xác nhận lựa chọn feature cuối cùng.",
        ])
    lines.extend([
        "", "## Known Limitations", "",
        "- Với prevalence 24,7% của toàn dataset, trần lý thuyết của Recall@10% là `0,10 / 0,247 ≈ 40,5%`; trên frozen test prevalence 24,5%, con số tương ứng là khoảng 40,8%. Vì vậy mục tiêu Recall@10% = 60% không thể đạt trực tiếp trên dataset này nếu không chuyển sang một giả định prevalence khác.",
        "- Nguồn gốc và quy trình xác lập nhãn `fraud_reported` chưa được kiểm chứng. Nhãn này có thể phản ánh fraud được báo cáo/phát hiện thay vì toàn bộ fraud thực tế.",
        "- Tín hiệu mạnh từ `insured_hobbies` chỉ là đặc điểm của dataset hiện tại và không được trình bày như một chỉ báo gian lận thực tế.",
        "- CarDD, CORD và Kaggle chưa có claim ID chung; kết quả này chỉ áp dụng cho nhánh tabular.",
        "- Kịch bản prevalence 5–10% chỉ là mô phỏng label shift, không phải kiểm định trên dữ liệu production.",
        "- Chưa có chi phí nghiệp vụ để tính Net Value; không suy ra hiệu quả tài chính hay production readiness.",
        "", "## Tệp kết quả", "",
        "- `reports/metrics/tabular_v1.json`: số liệu và metadata chi tiết.",
        "- `reports/metrics/tabular_bias_excluded_v1.json`: kết quả chi tiết của biến thể loại biased features.",
        "- `reports/leakage/`: audit chỉ trên train.",
        "- `artifacts/shap/tabular_v1/` và `reports/figures/shap_global.png`: giải thích mô hình.",
    ])
    if robustness:
        full = result["cv"]["xgboost"]["average_precision"]
        profiles = robustness["profiles"]
        complete = profiles.get("stage3_complete", profiles.get("no_social_proxy"))["average_precision_mean"]
        intake = profiles.get("stage1_intake", profiles.get("early_claim_candidate"))["average_precision_mean"]
        lines.extend(["", f"Train-only CV Average Precision theo nhóm feature: mô hình nghiên cứu đầy đủ {full:.3f}, hồ sơ đủ chứng từ {complete:.3f}, lúc tiếp nhận {intake:.3f}. Chưa xác nhận thời điểm có sẵn của mọi trường."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    destination = ROOT / "reports/RESULTS.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(), encoding="utf-8")
    print(destination)
