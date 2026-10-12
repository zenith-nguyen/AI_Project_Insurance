# Provenance và cách diễn giải nhãn `fraud_reported` — v1

**Ngày cập nhật:** 12/10/2026  
**Kết luận quản trị:** dùng như **observed fraud status** cho baseline nghiên cứu; chưa xem là verified ground truth cho production.

## Bằng chứng hiện có

- Dataset có 1.000 hồ sơ, 247 `Y` và 753 `N`. Một nghiên cứu dùng cùng dữ liệu diễn giải target là fraudulent/legitimate claims, nhưng cách sử dụng target trong nghiên cứu không tự chứng minh quy trình adjudication ban đầu: [Discover Artificial Intelligence, 2026](https://link.springer.com/article/10.1007/s44163-026-01952-3).
- Metadata của [Mendeley Data](https://data.mendeley.com/datasets/992mh7dk9y/2) nói dữ liệu có phản hồi chuyên gia và trải qua kiểm tra thủ công/tự động. Tuy nhiên, metadata không cung cấp tiêu chí kết luận, danh tính/vai trò adjudicator, thời điểm chốt nhãn, trạng thái appeal, hay bằng chứng rằng từng nhãn `N` đã được điều tra và xác nhận không gian lận.
- File nguồn chỉ cung cấp giá trị nhị phân Y/N, không có trường provenance hoặc audit trail đi kèm.

Vì vậy, bằng chứng công khai hỗ trợ việc dùng target cho benchmark, nhưng chưa đủ để khẳng định:

```text
Y = confirmed fraud
N = confirmed non-fraud
```

Khả năng thận trọng hơn là:

```text
N = không được ghi nhận là fraud trong dữ liệu
  = legitimate + fraud chưa phát hiện/không được báo cáo (có thể có)
```

## Tác động đến mô hình và metric

XGBoost v1 đang ước lượng gần với `P(fraud_reported = Y | X)`. Nếu target phản ánh khả năng bị phát hiện/báo cáo, output chưa thể diễn giải là `P(actual fraud | X)`.

- Recall@10% = 22,4% nghĩa là tìm lại 22,4% các hồ sơ có nhãn quan sát `Y`, chưa chứng minh tìm được 22,4% toàn bộ gian lận thực tế.
- AP, ROC-AUC, Brier và ECE đều được đánh giá theo nhãn quan sát này.
- Nhãn `N` có thể chứa false negative tiềm ẩn, gây label noise và làm sai calibration.
- Tỷ lệ `Y` 24,7% khác giả định production 5–10%, nên probability sau calibration chưa dùng như xác suất production.

## Chấm theo rubric Layer B

| Tiêu chí | Điểm | Lý do |
|---|---:|---|
| C1 — Nguồn gốc | 0/2 | Không có lineage/adjudicator có thể audit từ file dự án |
| C2 — Khả năng đối chiếu | 0/2 | Không có case evidence hoặc kết luận điều tra để kiểm tra từng nhãn |
| C3 — Đầy đủ | 2/2 | Không missing trong 1.000 dòng |
| C4 — Cơ sở nghiệp vụ | 1/2 | Ý nghĩa target rõ ở mức khái quát, quy trình xác lập chưa rõ |
| **Tổng** | **3/8 — Thấp** | Đủ cho PoC/baseline, chưa đủ cho production claim |

## Chính sách dự án

1. Gọi target là `observed fraud status`, không viết “confirmed fraud ground truth”.
2. Không tự động từ chối claim từ output model.
3. Model Card phải gắn giới hạn provenance cạnh mọi metric tabular.
4. Khi có dữ liệu thật, label contract tối thiểu phải có: `label`, `label_status`, `adjudicated_at`, `adjudicator_role`, `evidence_refs`, `appeal_status`, `label_version` và lý do kết luận.
5. Cần external validation và sensitivity analysis với label noise trước pilot.

