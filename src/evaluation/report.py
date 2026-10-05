"""Render reproducible, human-readable experiment results."""
from __future__ import annotations

import json

from src.data.common import ROOT


def render() -> str:
    result = json.loads((ROOT / "reports/metrics/tabular_v1.json").read_text(encoding="utf-8"))
    test, rule, intervals = result["test"], result["rule_baseline_test"], result["test_ci_95"]
    ops = result["test_operations"]
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
        "", "## Các giới hạn bắt buộc ghi trong đồ án", "",
        "- CarDD, CORD và Kaggle chưa có claim ID chung; kết quả này chỉ áp dụng cho nhánh tabular.",
        "- Nguồn nhãn `fraud_reported`, thời điểm có sẵn của các feature và chất lượng dữ liệu cần chuyên gia nghiệp vụ xác nhận.",
        "- Kịch bản prevalence 5–10% chỉ là mô phỏng label shift, không phải kiểm định trên dữ liệu production.",
        "- Chưa có chi phí nghiệp vụ để tính Net Value; không suy ra hiệu quả tài chính.",
        "- SHAP giải thích đóng góp vào dự đoán của mô hình, không kết luận khách hàng gian lận hay quan hệ nhân quả.",
        "", "## Tệp kết quả", "",
        "- `reports/metrics/tabular_v1.json`: số liệu và metadata chi tiết.",
        "- `reports/leakage/`: audit chỉ trên train.",
        "- `artifacts/shap/tabular_v1/` và `reports/figures/shap_global.png`: giải thích mô hình.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    destination = ROOT / "reports/RESULTS.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(), encoding="utf-8")
    print(destination)
