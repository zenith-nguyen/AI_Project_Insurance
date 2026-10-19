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
