# 03 — Data và prediction contract

## Prediction CSV

Một file wide duy nhất:

```csv
claim_id,fraud_label,B0_score,B1_score,B2_score,B3_score,B4_score,B5_score
CLM-001,0,0.12,0.18,0.20,,,
CLM-002,1,0.72,0.81,0.86,,,
```

Quy tắc:

- `claim_id` duy nhất, không null;
- `fraud_label` chỉ 0/1 và phải có cả hai lớp;
- mỗi stage được đánh giá phải có score cho tất cả claim;
- không điền `0` thay cho module thiếu; để trống và stage sẽ được ghi `not evaluated`;
- score phải finite; không NaN một phần;
- tất cả stage dùng cùng label và cùng hàng.

## Data tối thiểu cho B3–B5

| Nhóm | Field bắt buộc |
|---|---|
| Claim | `claim_id`, label, `scored_at`, tabular features |
| Document | `claim_id`, `document_id`, `received_at`, type, extracted field, confidence, missing/error state |
| Image | `claim_id`, `evidence_id`, `received_at`, damage classes/area/confidence, authenticity/reuse state |
| Relationship | entity type/value đã chuẩn hóa hoặc hash, `available_at`, related claim count, temporal distance |
| Audit | pipeline/model version, feature schema hash, prediction timestamp |

## Feature aggregation đề xuất

Không đưa raw ảnh/raw token trực tiếp vào XGBoost phase này. Tạo feature có nghĩa:

- Document: số chứng từ, loại chứng từ thiếu, confidence thấp nhất/trung bình, field conflict count, correction-required flag.
- Image: số vùng hư hỏng, diện tích mask tương đối, class count, max/mean confidence, reuse/metadata/editing flags.
- Graph: shared entity count, related claim count trước thời điểm chấm, cluster size point-in-time, shortest path count.
- Consistency: amount/date/plate mismatch flags và confidence.

Mọi feature phải có data dictionary: định nghĩa, kiểu, missing policy, thời điểm xuất hiện, owner và leakage decision.

## Hash và provenance

Mỗi run phải lưu:

- input file SHA-256;
- split manifest/hash;
- code commit;
- config hash;
- seed;
- model artifact hash;
- prediction hash;
- thời điểm chạy UTC;
- người chạy.
