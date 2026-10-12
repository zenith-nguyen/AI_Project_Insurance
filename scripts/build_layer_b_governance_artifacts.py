"""Build the stage/reliability governance table for the 39 Layer-B fields."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = ROOT / "reports/handoff/data_dictionary.md"
CSV_OUTPUT = ROOT / "configs/layer_b_field_governance_v1.csv"
REPORT_OUTPUT = ROOT / "reports/LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md"

FIELDS = [
    "months_as_customer", "age", "policy_number", "policy_bind_date",
    "policy_state", "policy_csl", "policy_deductable", "policy_annual_premium",
    "umbrella_limit", "insured_zip", "insured_sex", "insured_education_level",
    "insured_occupation", "insured_hobbies", "insured_relationship", "capital_gains",
    "capital_loss", "incident_date", "incident_type", "collision_type",
    "incident_severity", "authorities_contacted", "incident_state", "incident_city",
    "incident_location", "incident_hour_of_the_day", "number_of_vehicles_involved",
    "property_damage", "bodily_injuries", "witnesses", "police_report_available",
    "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
    "auto_make", "auto_model", "auto_year", "fraud_reported",
]

STAGES = [
    "Intake", "Intake", "Intake", "Intake", "Intake", "Intake", "Intake", "Intake",
    "Intake", "Intake", "Intake", "Intake", "Intake", "Intake", "Intake", "Intake",
    "Intake", "Intake", "Intake", "Intake", "Sau giám định", "Intake", "Intake",
    "Intake", "Intake", "Intake", "Intake", "Intake", "Intake", "Đủ chứng từ",
    "Đủ chứng từ", "Sau giám định", "Sau giám định", "Sau giám định", "Sau giám định",
    "Intake", "Intake", "Intake", "Sau điều tra",
]

STAGE_CONFIDENCE = [
    *(["Cao"] * 15), "Thấp", "Thấp", "Trung bình", "Trung bình", "Trung bình",
    "Thấp", "Trung bình", "Trung bình", "Trung bình", "Trung bình", "Trung bình",
    "Trung bình", "Trung bình", "Trung bình", "Thấp", "Trung bình", "Thấp", "Thấp",
    "Thấp", "Thấp", "Cao", "Cao", "Cao", "Thấp",
]

RELIABILITY_SCORE = [
    8, 8, 8, 8, 8, 8, 8, 8, 8, 5, 6, 3, 5, 2, 5, 2, 2, 6, 6, 5,
    5, 5, 6, 6, 4, 6, 6, 3, 6, 6, 4, 6, 6, 6, 6, 8, 8, 8, 3,
]

RELIABILITY_LEVEL = [
    "Cao", "Cao", "Cao", "Cao", "Cao", "Cao", "Cao", "Cao", "Cao",
    "Trung bình", "Trung bình", "Thấp", "Trung bình", "Thấp", "Trung bình",
    "Thấp", "Thấp", "Trung bình", "Trung bình", "Trung bình", "Trung bình",
    "Trung bình", "Trung bình", "Trung bình", "Trung bình", "Trung bình",
    "Trung bình", "Thấp", "Trung bình", "Trung bình", "Trung bình",
    "Trung bình", "Trung bình", "Trung bình", "Trung bình", "Cao", "Cao", "Cao",
    "Thấp",
]

MISSING_RATE = {"collision_type": 17.8, "authorities_contacted": 9.1,
                "property_damage": 36.0, "police_report_available": 34.3}

FEATURE_POLICY = {
    "policy_number": "Loại: identifier",
    "policy_bind_date": "Chỉ dùng để tạo policy_age_days",
    "incident_date": "Chỉ dùng để tạo policy_age_days; stage theo snapshot",
    "insured_zip": "Loại: proxy địa lý/cardinality cao",
    "insured_sex": "Nhạy cảm; fairness audit, không dùng để tự động từ chối",
    "insured_education_level": "Proxy nhân khẩu học; sensitivity/fairness review",
    "insured_occupation": "Proxy nhân khẩu học; sensitivity/fairness review",
    "insured_hobbies": "Loại ở biến thể bias-aware; provenance/nghiệp vụ yếu",
    "capital_gains": "Loại cho production đến khi xác minh ngữ nghĩa",
    "capital_loss": "Loại cho production đến khi xác minh ngữ nghĩa",
    "incident_location": "Loại: proxy địa lý/cardinality cao",
    "total_claim_amount": "Loại ở baseline do dư thừa với ba claim component",
    "fraud_reported": "Target only; cấm làm feature",
}

STAGE_REASON = {
    "incident_severity": "Giá trị chính thức cần giám định; FNOL có thể chỉ là ước tính",
    "witnesses": "Chọn bảo thủ: cần biên bản/lời khai hoàn chỉnh",
    "police_report_available": "Chỉ xác nhận khi hồ sơ đã nhận biên bản",
    "total_claim_amount": "Giá trị đánh giá cần báo giá/giám định",
    "injury_claim": "Giá trị đánh giá cần hồ sơ y tế/giám định",
    "property_claim": "Giá trị đánh giá cần báo giá/chứng từ",
    "vehicle_claim": "Giá trị đánh giá cần báo giá gara/giám định",
    "fraud_reported": "Kết quả quan sát sau điều tra; không có tại thời điểm scoring",
    "capital_gains": "Giả định có tại intake nhưng ngữ nghĩa nguồn chưa xác minh",
    "capital_loss": "Giả định có tại intake nhưng ngữ nghĩa nguồn chưa xác minh",
}


def dictionary_rows() -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for line in DICTIONARY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        field = cells[0].strip("`")
        rows[field] = (re.sub(r"`", "", cells[3]), cells[4])
    return rows


def main() -> None:
    if not (len(FIELDS) == len(STAGES) == len(STAGE_CONFIDENCE)
            == len(RELIABILITY_SCORE) == len(RELIABILITY_LEVEL) == 39):
        raise RuntimeError("Layer-B governance arrays must contain exactly 39 fields")

    descriptions = dictionary_rows()
    rows = []
    for index, field in enumerate(FIELDS):
        description, source = descriptions[field]
        rows.append({
            "ordinal": index + 1,
            "field": field,
            "meaning": description,
            "source": source,
            "available_stage": STAGES[index],
            "stage_confidence": STAGE_CONFIDENCE[index],
            "stage_reason": STAGE_REASON.get(field, "Theo hợp đồng/FNOL và benchmark vòng đời claim"),
            "missing_rate_percent": MISSING_RATE.get(field, 0.0),
            "reliability_score_8": RELIABILITY_SCORE[index],
            "reliability_level": RELIABILITY_LEVEL[index],
            "feature_policy": FEATURE_POLICY.get(field, "Chỉ dùng khi có tại scoring snapshot và qua feature policy"),
        })

    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    stage_counts = Counter(row["available_stage"] for row in rows)
    reliability_counts = Counter(row["reliability_level"] for row in rows)
    lines = [
        "# Data Dictionary theo Stage và Độ tin cậy — Layer B v1",
        "",
        "**Ngày khóa bản:** 12/10/2026  ",
        "**Phạm vi:** 39 cột nguồn của Bronze Layer B. `claim_id`, `source_row` và `fraud_label` là cột engineered nên không nằm trong bảng này.",
        "",
        "## Rubric",
        "",
        "Thời điểm có sẵn được xác định bảo thủ theo thứ tự: kết quả điều tra → `Sau điều tra`; cần chứng từ phát hành sau sự cố → `Đủ chứng từ`; cần giám định/báo giá bên thứ ba → `Sau giám định`; còn lại → `Intake`. Khi chưa chắc, chọn stage muộn hơn để hạn chế leakage.",
        "",
        "Độ tin cậy chấm bốn tiêu chí 0–2: nguồn gốc, khả năng đối chiếu, đầy đủ và cơ sở nghiệp vụ. Tổng 7–8 là Cao, 4–6 là Trung bình, 0–3 là Thấp. Ngưỡng completeness 5%/20% là quy ước dự án, không phải ngưỡng do ISO/IEC 25012 quy định.",
        "",
        f"Phân bố stage: {dict(stage_counts)}. Phân bố reliability: {dict(reliability_counts)}.",
        "",
        "## Bảng 39 trường",
        "",
        "| # | Trường | Ý nghĩa | Stage | Chắc chắn stage | Missing | Tin cậy | Feature policy |",
        "|---:|---|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['ordinal']} | `{row['field']}` | {row['meaning']} | {row['available_stage']} | "
            f"{row['stage_confidence']} | {row['missing_rate_percent']:.1f}% | "
            f"{row['reliability_level']} ({row['reliability_score_8']}/8) | {row['feature_policy']} |"
        )
    lines += [
        "",
        "## Quy tắc sử dụng",
        "",
        "- Mỗi model stage chỉ nhận trường có `available_stage` không muộn hơn thời điểm scoring của stage đó.",
        "- `fraud_reported` chỉ dùng làm observed target sau điều tra; không được dùng làm feature.",
        "- Reliability và feature policy là hai đánh giá khác nhau. Một trường đầy đủ vẫn có thể bị loại vì nhạy cảm, proxy hoặc thiếu cơ sở nghiệp vụ.",
        "- Bốn tỷ lệ thiếu khác 0 được đo trong audit Silver. Các trường còn lại có tỷ lệ missing 0% trong bản dữ liệu hiện tại; điều này không chứng minh dữ liệu đúng về nghiệp vụ.",
        "- Các trường stage-confidence Thấp phải được xác nhận với nghiệp vụ trước pilot.",
        "",
        "## Căn cứ",
        "",
        "- [ISO/IEC 25012:2008 — Data quality model](https://www.iso.org/obp/ui/#iso:std:iso-iec:25012:ed-1:v1:en)",
        "- `reports/handoff/data_audit_report.md` — missing/profile thực nghiệm.",
        "- `reports/handoff/data_dictionary.md` — tên, kiểu và lineage Bronze/Silver.",
        "- `reports/FEATURE_POLICY.md` — chính sách feature hiện hành.",
        "",
        f"Bản máy đọc: `configs/{CSV_OUTPUT.name}`.",
    ]
    REPORT_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {CSV_OUTPUT}")
    print(f"Built {REPORT_OUTPUT}")


if __name__ == "__main__":
    main()
