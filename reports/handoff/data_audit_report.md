# Data Audit Report — Layer B

## EDA đã xác minh

- Bronze: 1.000 dòng × 39 cột. Silver: 1.000 dòng × 42 cột.
- Phân bố target: 753 non-fraud (75,3%) và 247 fraud (24,7%).
- Silver có `claim_id` và `source_row` unique; `fraud_label` khớp `fraud_reported`.
- Placeholder `?` đã được chuyển thành missing value; không còn `?` trong Silver.

| Cột có missing | Số dòng | Tỷ lệ |
|---|---:|---:|
| `property_damage` | 360 | 36,0% |
| `police_report_available` | 343 | 34,3% |
| `collision_type` | 178 | 17,8% |
| `authorities_contacted` | 91 | 9,1% |

Missing categorical được giữ thành tín hiệu rõ ràng và chỉ impute trong pipeline fit trên train. Silver không impute, encode hoặc scale.

## Leakage và feature policy

- Loại identifier/trace/target: `claim_id`, `source_row`, `policy_number`, `fraud_reported`, `fraud_label`.
- Loại proxy/cardinality cao: `insured_zip`, `incident_location`; biến thể bias-aware loại thêm `insured_hobbies`.
- `total_claim_amount = injury_claim + property_claim + vehicle_claim` trên 100% dòng train. Đây là redundancy, không tự động chứng minh target leakage; baseline loại tổng tiền và giữ components để tránh trùng thông tin.
- Raw dates được loại; `policy_age_days` được tính từ ngày hợp đồng và ngày sự cố.
- `incident_severity`, claim components, police report, witnesses và bodily injuries cần xác nhận có sẵn ở checkpoint nào trước khi dùng production.

Kết luận: audit đủ cho baseline nghiên cứu; provenance của nhãn và thời điểm có dữ liệu vẫn là hai rủi ro chính.
