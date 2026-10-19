# PHASE 5 — BASELINE B0–B5 & EVALUATION HANDOFF

**Ngày cập nhật:** 19/10/2026
**Dự án:** AI Project Insurance
**Mục đích:** tài liệu bàn giao cho thành viên phụ trách baseline, bootstrap và evaluation report.

---

# Phase 5 — Baseline & Evaluation handoff kit

**Ngày cập nhật:** 19/10/2026
**Người nhận:** thành viên phụ trách Baseline B0–B5 và Evaluation Report

## Đọc theo thứ tự

1. `01_TASK_BRIEF_AND_B0_B5.md` — phạm vi, định nghĩa B0–B5 và điều được phép kết luận.
2. `02_EXPERIMENT_PROTOCOL.md` — split, leakage gate, metric, paired bootstrap và biểu đồ.
3. `03_DATA_AND_PREDICTION_CONTRACT.md` — dữ liệu/format cần giao giữa người train và người evaluation.
4. `04_RUNBOOK.md` — lệnh chạy và output cần nộp.
5. `05_REPORT_TEMPLATE.md` — khung Baseline & Evaluation Report.
6. `06_REVIEW_CHECKLIST.md` — checklist review/Definition of Done.
7. `phase5_predictions_SCHEMA_EXAMPLE.csv` — file giả chỉ để kiểm tra format, tuyệt đối không dùng làm kết quả.
8. `07_REFERENCE_MAP.md` — bản đồ file evidence hiện có trong repo.

## Code đã chuẩn bị

- Cấu hình: `configs/phase5_evaluation.v1.yaml`
- Evaluator: `scripts/evaluate_phase5_baselines.py`
- Paired CI: `src/evaluation/metrics.py::paired_stratified_bootstrap`

## Điều quan trọng nhất

Hiện có thể phát triển B0–B2 bằng dữ liệu tabular `train_fs/val_fs`. B3–B5 chỉ được tính PR-AUC/Recall@K khi ảnh, chứng từ, quan hệ và nhãn thuộc **cùng claim_id**, đồng thời mọi dữ liệu đầu vào đã tồn tại trước `scored_at`.

Không ghép hàng Kaggle, ảnh CarDD và hóa đơn SROIE thành một “claim” giả để công bố metric B3–B5.

---

# 01 — Task brief và định nghĩa B0–B5

## Mục tiêu

Xây chuỗi ablation tăng dần từ rule đơn giản đến pipeline đầy đủ và trả lời ba câu hỏi:

1. Candidate có xếp hạng claim tốt hơn baseline không?
2. Module mới đóng góp thêm bao nhiêu trên **cùng claim/split**?
3. Mức tăng có đủ ổn định hay CI 95% của hiệu số vẫn chứa 0?

Hệ thống hỗ trợ ưu tiên hồ sơ cho con người. Score không phải xác suất gian lận production và không được dùng một mình để từ chối bồi thường.

## Định nghĩa khóa

| Stage | Thành phần | Input hợp lệ | Trạng thái dữ liệu hiện tại |
|---|---|---|---|
| B0 | Rule baseline | Dữ liệu bảng của claim | Chạy được |
| B1 | Logistic Regression | Cùng feature/split tabular với B0/B2 | Chạy được |
| B2 | XGBoost tabular | Dữ liệu bảng, chưa dùng ảnh/chứng từ/graph | Chạy được |
| B3 | B2 + document signals | OCR/KIE/classification của cùng claim, `received_at <= scored_at` | Chờ claim-linked labeled data |
| B4 | B3 + image signals | Damage/authenticity của ảnh cùng claim | Chờ claim-linked labeled data |
| B5 | B4 + consistency/relationship | Feature graph point-in-time, edge `available_at <= scored_at` | Chờ claim-linked labeled data |

Định nghĩa này phải được khóa trước khi mở external test. Nếu rubric chính thức của môn học có định nghĩa B0–B5 khác, cập nhật YAML và biên bản thay đổi trước khi chạy.

## Deliverables bắt buộc

- prediction CSV cho từng stage trên đúng cùng claim;
- bảng AP, Recall@5/10/20%, Precision@5/10/20%;
- bootstrap CI 95% riêng từng model và paired delta CI cho B1–B0, B2–B0, B2–B1, B5–B2;
- PR curves và Recall/Precision@K curves;
- error analysis ở top queue;
- model/data/split hash, seed và version;
- kết luận trung thực khi CI chứa 0;
- Baseline & Evaluation Report hoàn chỉnh.

## Phần nhóm đã có sẵn

- B0 rule implementation: `src/baselines/rules.py`.
- B1/B2 model factory và preprocessing: `src/models/train.py`.
- Metric/top-K/bootstrap: `src/evaluation/metrics.py`.
- Split phát triển mới: `data/gold/feature_selection_v1/{train_fs,val_fs}.parquet`.
- Baseline ownership: `configs/baseline_registry.v1.yaml`.

## Phần người nhận task phải làm

1. Xác nhận field nào có sẵn ở từng thời điểm chấm.
2. Tạo predictions B0–B2 trên `val_fs` mà không đọc test cũ để chọn feature/model.
3. Chuẩn bị data contract B3–B5 và đánh dấu blocked nếu chưa có claim-linked labels.
4. Chạy evaluator, đọc paired CI, viết error analysis và báo cáo.
5. Không biến engineering PASS của graph/OCR/YOLO thành PR-AUC của claim fraud.

---

# 02 — Experiment protocol

## Split policy

### Development hiện tại

- `train_fs`: 560 claim, 138 positive.
- `val_fs`: 140 claim, 35 positive.
- Hai split được tạo chỉ từ original train, không trùng claim ID.
- Mọi lựa chọn feature/cấu hình mới dùng hai split này.

### Frozen test cũ

Test 200 claim đã được dùng cho baseline v1 và một sensitivity analysis. Nó được xem là **spent for feature-policy decisions**. Không dùng test này để chọn B3–B5, threshold hoặc feature.

### Final evaluation mới

Cần external claim-linked test mới sau khi khóa:

- định nghĩa B0–B5;
- feature schema và time availability;
- model/hyperparameter;
- calibration;
- queue K và paired comparisons;
- policy missing input/fallback.

## Leakage gates

Một run chỉ hợp lệ khi:

- preprocessing fit trong train/fold;
- feature không chứa target hoặc proxy sau quyết định;
- document/image phải thuộc cùng `claim_id`;
- `received_at <= scored_at`;
- graph edge có `available_at <= scored_at`;
- threshold chọn từ validation;
- test không được dùng để sửa pipeline;
- B0–B5 prediction cùng claim/order/label.

## Metric

Primary metric của repo là **Average Precision (AP)**, thường được trình bày như summary của đường PR. Khi viết “PR-AUC”, phải ghi rõ đang dùng AP hay trapezoidal AUC; không trộn hai định nghĩa.

Operational metrics:

- Recall@K: trong toàn bộ positive, bao nhiêu được đưa vào top K% hàng đợi;
- Precision@K: trong top K% hàng đợi, bao nhiêu là positive;
- K mặc định: 5%, 10%, 20%;
- queue size dùng `ceil(n × K)` và stable tie order;
- calibration: Brier/ECE chỉ áp dụng khi score được diễn giải là probability đã calibration.

## Bootstrap 1.000 lần

### CI từng model

Resample positive và negative riêng, có hoàn lại, giữ số lượng mỗi lớp. Báo percentile 2,5% và 97,5%.

### CI hiệu số

Để so B5 với B2, dùng **cùng indices bootstrap cho cả hai model**:

```text
delta_draw = metric(B5 on draw) - metric(B2 on same draw)
```

Diễn giải:

- CI hoàn toàn > 0: candidate tốt hơn có bằng chứng trên sample hiện tại;
- CI chứa 0: chưa đủ bằng chứng khác biệt;
- CI hoàn toàn < 0: candidate kém hơn;
- không được viết “không khác biệt” thành “hai model bằng nhau”.

## Error analysis bắt buộc

Với K=10%, xuất tối thiểu:

- positive bị bỏ khỏi queue;
- negative bị đưa vào queue;
- claim thay đổi vị trí mạnh nhất giữa B5 và B2;
- missing module/fallback;
- nhóm input và feature tạo cờ;
- kiểm tra theo thời điểm để loại leakage.

Không dùng chính các lỗi trong final test để tune lại model.

---

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

---

# 04 — Runbook

## 1. Chuẩn bị môi trường

```powershell
cd D:\AI_Project_Insurance
.\.venv\Scripts\python.exe -m pytest tests\test_metrics.py -q
```

## 2. Kiểm tra dữ liệu development

```powershell
Get-Content data\gold\feature_selection_v1\manifest.json
```

Xác nhận hash `train_fs` và `val_fs` khớp manifest. Không thay file và giữ nguyên seed.

## 3. Sinh prediction

Người train phải xuất file theo `phase5_predictions_SCHEMA_EXAMPLE.csv`. B0–B2 chạy trên cùng `val_fs`. B3–B5 để trống nếu chưa có claim-linked labels.

Không dùng `src/models/train_stages.py` hiện tại làm kết quả Phase 5 nếu script còn đọc `dataset_v2/test.parquet`; phải chuyển nó sang `train_fs/val_fs` trước.

## 4. Chạy evaluator

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_phase5_baselines.py `
  path\to\phase5_predictions.csv `
  --config configs\phase5_evaluation.v1.yaml `
  --output-dir reports\phase5 `
  --dataset-name feature_selection_v1_val_fs
```

Output:

```text
reports/phase5/
├── phase5_metrics.json
├── PHASE5_EVALUATION_REPORT.md
├── phase5_pr_curves.png
└── phase5_at_k.png
```

## 5. Đọc paired comparison

Trong `phase5_metrics.json`:

```json
{
  "delta": 0.03,
  "lower": -0.01,
  "upper": 0.08,
  "contains_zero": true
}
```

Kết luận: candidate có point estimate cao hơn 0,03 nhưng CI chứa 0, nên chưa đủ bằng chứng candidate tốt hơn.

## 6. Trước khi nộp

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git status --short
```

Chỉ commit source/config/report cần thiết. Prediction chứa dữ liệu thật hoặc PII không được đẩy lên GitHub public.

---

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

---

# 06 — Review checklist và Definition of Done

## Data

- [ ] Cùng `claim_id` giữa label, tabular, document, image và graph.
- [ ] Không có cross-split duplicate/leakage.
- [ ] Mọi feature có `available_at/received_at <= scored_at`.
- [ ] Train/validation/test hash được lưu.
- [ ] PII không vào GitHub public.

## Experiment

- [ ] B0–B5 được khóa trước final test.
- [ ] B0/B1/B2 dùng cùng feature eligibility và split.
- [ ] Preprocessing fit trong fold/train.
- [ ] Threshold/calibration không fit bằng test.
- [ ] Seed/config/dependency/model hash được ghi.

## Evaluation

- [ ] AP, Recall@5/10/20%, Precision@5/10/20%.
- [ ] Bootstrap phân tầng 1.000 lần.
- [ ] Paired delta CI cho comparison đã khóa.
- [ ] PR curve và Recall/Precision@K curve.
- [ ] CI chứa 0 được kết luận “chưa đủ bằng chứng”.
- [ ] Error analysis top queue.

## Business

- [ ] Nói rõ score dùng xếp hàng, không kết luận fraud.
- [ ] K gắn với năng lực review.
- [ ] Có latency và fallback khi module thiếu.
- [ ] Có false hold/false investigation discussion.
- [ ] B3–B5 blocked nếu chưa có claim-linked labeled data.

## Definition of Done

Task chỉ DONE khi code chạy lại được, evidence có hash, report khớp JSON, reviewer kiểm tra leakage/comparison và mọi limitation được ghi. Nếu chưa có external claim-linked test, trạng thái tối đa là **development evaluation complete**, không phải final/production validated.

---

# 07 — Reference map

| Cần đọc | File |
|---|---|
| Baseline ownership | `configs/baseline_registry.v1.yaml` |
| Phase 5 B0–B5 config | `configs/phase5_evaluation.v1.yaml` |
| Gold split và test policy | `README.md`, `data/gold/feature_selection_v1/manifest.json` |
| Feature policy | `configs/features.yaml` |
| Stage feature proposal | `configs/stages.yaml` |
| Rule baseline | `src/baselines/rules.py` |
| Model training | `src/models/train.py` |
| Metric/bootstrap | `src/evaluation/metrics.py` |
| Current tabular results | `reports/RESULTS.md` |
| Feature-policy validation | `reports/FEATURE_POLICY.md` |
| Robustness | `reports/ROBUSTNESS.md` |
| Baseline explanation | `reports/BASELINE_CLARIFICATION_AND_UPGRADE_2026-10-17.md` |
| Model limitation | `docs/handbook/04_MODELS_METRICS_AND_LIMITATIONS.md` |

## Historical numbers for context only

- Frozen test B0 rule: AP 0,424; Recall@10% 16,3%; Precision@10% 40,0%.
- Frozen test XGBoost v1: AP 0,559; Recall@10% 22,4%; Precision@10% 55,0%.
- Train repeated CV: Logistic AP 0,671; XGBoost AP 0,706.
- `val_fs` feature-policy result: research_full AP 0,670; bias-excluded AP 0,598; stage1 AP 0,267; stage3 AP 0,500.

Không đặt các số thuộc CV, val_fs và frozen test vào cùng một hàng rồi tính hiệu số.

---

# Tin nhắn gửi thành viên phụ trách

Bạn phụ trách **Phase 5 — Baseline B0–B5 & Evaluation Report**. Mình đã chuẩn bị task brief, protocol chống leakage, data contract, runbook, report template, checklist và evaluator trong gói này.

Việc đầu tiên là đọc `00_README.md` rồi xác nhận định nghĩa B0–B5 trong `configs/phase5_evaluation.v1.yaml`. Trước mắt chạy B0 Rule, B1 Logistic Regression và B2 XGBoost trên cùng `train_fs/val_fs`. B3–B5 chỉ được đánh giá khi document/image/graph thật sự thuộc cùng `claim_id` và có timestamp trước lúc chấm; không ghép Kaggle, CarDD và SROIE thành claim giả.

Output cần có AP, Recall/Precision@5/10/20%, PR curve, paired bootstrap 1.000 lần và CI hiệu số. Nếu CI chứa 0, kết luận là “chưa đủ bằng chứng candidate tốt hơn”. Frozen test cũ không được dùng để chọn feature/cấu hình mới. Khi có prediction CSV đúng schema, chạy lệnh trong `04_RUNBOOK.md`.
