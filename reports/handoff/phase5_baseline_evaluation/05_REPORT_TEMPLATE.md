# 05 — Baseline & Evaluation Report template

## 1. Executive summary

- B-stage cao nhất đã đánh giá:
- Dataset/split:
- Primary metric:
- Candidate được chọn:
- Candidate có vượt baseline không:
- CI hiệu số có chứa 0 không:
- Kết luận nghiệp vụ:
- Điều chưa được phép tuyên bố:

## 2. Scope và câu hỏi nghiên cứu

Nêu rõ xếp hạng hàng đợi, không phải quyết định gian lận tự động.

## 3. Data lineage và leakage control

| Dataset | Vai trò | Rows/positives | Hash | Test status |
|---|---|---:|---|---|
| train_fs | fit/CV | | | không dùng final claim |
| val_fs | development evaluation | | | dùng chọn candidate |
| external test | final | | | chỉ mở sau freeze |

## 4. B0–B5 definitions

Sao chép định nghĩa đã khóa từ YAML; ghi rõ stage nào blocked và lý do.

## 5. Model selection

Nêu model candidates, preprocessing-in-fold, calibration, primary metric và tie-break.

## 6. Kết quả

| Stage | AP | Recall@5% | Recall@10% | Recall@20% | Precision@10% | Latency |
|---|---:|---:|---:|---:|---:|---:|

## 7. Paired bootstrap

| Comparison | Metric | Delta | CI 95% | Contains zero | Decision |
|---|---|---:|---:|---|---|

## 8. Curves

Chèn PR curve và Recall/Precision@K. Mỗi curve ghi dataset và số positive.

## 9. Error analysis

Tóm tắt false queue/false miss, nhóm feature, missing module và các case cần business review.

## 10. Business interpretation

- Với cùng năng lực review K%, thêm bao nhiêu positive được đưa lên?
- Precision hàng đợi thay đổi thế nào?
- Thời gian/chi phí module mới có xứng đáng không?
- False hold hoặc false investigation có tăng không?

## 11. Limitations

Nhãn, prevalence, domain shift, data size, CI, missing inputs, claim linkage, PII và UAT.

## 12. Reproducibility

Commit, config, seed, environment, hashes, commands và output paths.

## 13. Decision

Chọn một: `promote`, `continue research`, `reject`, `not evaluable`. Ghi căn cứ và next action.
