# Data Dictionary theo Stage và Độ tin cậy — Layer B v1

**Ngày khóa bản:** 12/10/2026  
**Phạm vi:** 39 cột nguồn của Bronze Layer B. `claim_id`, `source_row` và `fraud_label` là cột engineered nên không nằm trong bảng này.

## Rubric

Thời điểm có sẵn được xác định bảo thủ theo thứ tự: kết quả điều tra → `Sau điều tra`; cần chứng từ phát hành sau sự cố → `Đủ chứng từ`; cần giám định/báo giá bên thứ ba → `Sau giám định`; còn lại → `Intake`. Khi chưa chắc, chọn stage muộn hơn để hạn chế leakage.

Độ tin cậy chấm bốn tiêu chí 0–2: nguồn gốc, khả năng đối chiếu, đầy đủ và cơ sở nghiệp vụ. Tổng 7–8 là Cao, 4–6 là Trung bình, 0–3 là Thấp. Ngưỡng completeness 5%/20% là quy ước dự án, không phải ngưỡng do ISO/IEC 25012 quy định.

Phân bố stage: {'Intake': 31, 'Sau giám định': 5, 'Đủ chứng từ': 2, 'Sau điều tra': 1}. Phân bố reliability: {'Cao': 12, 'Trung bình': 21, 'Thấp': 6}.

## Bảng 39 trường

| # | Trường | Ý nghĩa | Stage | Chắc chắn stage | Missing | Tin cậy | Feature policy |
|---:|---|---|---|---|---:|---:|---|
| 1 | `months_as_customer` | Số tháng khách hàng gắn với doanh nghiệp | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 2 | `age` | Tuổi người được bảo hiểm | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 3 | `policy_number` | Mã hợp đồng; identifier, không dùng làm feature | Intake | Cao | 0.0% | Cao (8/8) | Loại: identifier |
| 4 | `policy_bind_date` | Ngày hợp đồng bắt đầu hiệu lực | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng để tạo policy_age_days |
| 5 | `policy_state` | Bang phát hành hợp đồng | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 6 | `policy_csl` | Mức giới hạn trách nhiệm kết hợp của hợp đồng | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 7 | `policy_deductable` | Mức khấu trừ; giữ chính tả của nguồn | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 8 | `policy_annual_premium` | Phí bảo hiểm năm | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 9 | `umbrella_limit` | Hạn mức bảo hiểm bổ sung | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 10 | `insured_zip` | Mã ZIP; proxy địa lý, đã loại khỏi model | Intake | Cao | 0.0% | Trung bình (5/8) | Loại: proxy địa lý/cardinality cao |
| 11 | `insured_sex` | Giới tính khai báo | Intake | Cao | 0.0% | Trung bình (6/8) | Nhạy cảm; fairness audit, không dùng để tự động từ chối |
| 12 | `insured_education_level` | Trình độ học vấn | Intake | Cao | 0.0% | Thấp (3/8) | Proxy nhân khẩu học; sensitivity/fairness review |
| 13 | `insured_occupation` | Nghề nghiệp | Intake | Cao | 0.0% | Trung bình (5/8) | Proxy nhân khẩu học; sensitivity/fairness review |
| 14 | `insured_hobbies` | Sở thích; proxy cần xem xét, đã loại trong một sensitivity check | Intake | Cao | 0.0% | Thấp (2/8) | Loại ở biến thể bias-aware; provenance/nghiệp vụ yếu |
| 15 | `insured_relationship` | Quan hệ của người được bảo hiểm với chủ hợp đồng | Intake | Cao | 0.0% | Trung bình (5/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 16 | `capital_gains` | Giá trị capital gains trong dữ liệu nguồn | Intake | Thấp | 0.0% | Thấp (2/8) | Loại cho production đến khi xác minh ngữ nghĩa |
| 17 | `capital_loss` | Giá trị capital loss trong dữ liệu nguồn | Intake | Thấp | 0.0% | Thấp (2/8) | Loại cho production đến khi xác minh ngữ nghĩa |
| 18 | `incident_date` | Ngày xảy ra sự cố | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng để tạo policy_age_days; stage theo snapshot |
| 19 | `incident_type` | Loại sự cố | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 20 | `collision_type` | Loại va chạm; 178 giá trị thiếu | Intake | Trung bình | 17.8% | Trung bình (5/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 21 | `incident_severity` | Mức độ nghiêm trọng khai báo/đánh giá | Sau giám định | Thấp | 0.0% | Trung bình (5/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 22 | `authorities_contacted` | Cơ quan chức năng được liên hệ; 91 thiếu | Intake | Trung bình | 9.1% | Trung bình (5/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 23 | `incident_state` | Bang xảy ra sự cố | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 24 | `incident_city` | Thành phố xảy ra sự cố | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 25 | `incident_location` | Địa điểm chi tiết; cardinality cao, đã loại | Intake | Trung bình | 0.0% | Trung bình (4/8) | Loại: proxy địa lý/cardinality cao |
| 26 | `incident_hour_of_the_day` | Giờ xảy ra sự cố, 0–23 | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 27 | `number_of_vehicles_involved` | Số xe liên quan | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 28 | `property_damage` | Có thiệt hại tài sản hay không; 360 thiếu | Intake | Trung bình | 36.0% | Thấp (3/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 29 | `bodily_injuries` | Số người bị thương | Intake | Trung bình | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 30 | `witnesses` | Số nhân chứng | Đủ chứng từ | Thấp | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 31 | `police_report_available` | Có báo cáo cảnh sát hay không; 343 thiếu | Đủ chứng từ | Trung bình | 34.3% | Trung bình (4/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 32 | `total_claim_amount` | Tổng tiền claim; bằng tổng ba component trên 100% train | Sau giám định | Thấp | 0.0% | Trung bình (6/8) | Loại ở baseline do dư thừa với ba claim component |
| 33 | `injury_claim` | Phần claim cho thương tích | Sau giám định | Thấp | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 34 | `property_claim` | Phần claim cho tài sản | Sau giám định | Thấp | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 35 | `vehicle_claim` | Phần claim cho xe | Sau giám định | Thấp | 0.0% | Trung bình (6/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 36 | `auto_make` | Hãng xe | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 37 | `auto_model` | Model xe; Silver ép string để tránh mixed type | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 38 | `auto_year` | Năm sản xuất xe | Intake | Cao | 0.0% | Cao (8/8) | Chỉ dùng khi có tại scoring snapshot và qua feature policy |
| 39 | `fraud_reported` | Nhãn gốc Y/N; không dùng làm feature | Sau điều tra | Thấp | 0.0% | Thấp (3/8) | Target only; cấm làm feature |

## Quy tắc sử dụng

- Mỗi model stage chỉ nhận trường có `available_stage` không muộn hơn thời điểm scoring của stage đó.
- `fraud_reported` chỉ dùng làm observed target sau điều tra; không được dùng làm feature.
- Reliability và feature policy là hai đánh giá khác nhau. Một trường đầy đủ vẫn có thể bị loại vì nhạy cảm, proxy hoặc thiếu cơ sở nghiệp vụ.
- Bốn tỷ lệ thiếu khác 0 được đo trong audit Silver. Các trường còn lại có tỷ lệ missing 0% trong bản dữ liệu hiện tại; điều này không chứng minh dữ liệu đúng về nghiệp vụ.
- Các trường stage-confidence Thấp phải được xác nhận với nghiệp vụ trước pilot.

## Căn cứ

- [ISO/IEC 25012:2008 — Data quality model](https://www.iso.org/obp/ui/#iso:std:iso-iec:25012:ed-1:v1:en)
- `reports/handoff/data_audit_report.md` — missing/profile thực nghiệm.
- `reports/handoff/data_dictionary.md` — tên, kiểu và lineage Bronze/Silver.
- `reports/FEATURE_POLICY.md` — chính sách feature hiện hành.

Bản máy đọc: `configs/layer_b_field_governance_v1.csv`.
