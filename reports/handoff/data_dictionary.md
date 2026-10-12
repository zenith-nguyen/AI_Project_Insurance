# Data Dictionary — Layer B

Đã kiểm tra từ workbook gốc và `claims_silver_v1.parquet`: Bronze có 39 cột; Silver có 42 cột, gồm 39 cột nguồn đã chuẩn hóa tên và 3 cột trace/target được tạo thêm. `string` là kiểu chuỗi nullable của pandas; `Int64` là số nguyên nullable.

Bronze giữ cùng kiểu numeric/date như bảng dưới; các cột categorical được đọc là `str`, riêng `auto_model` là `object` do mixed values. Silver chuẩn hóa toàn bộ categorical thành `string`.

| Silver column | Silver dtype | Tên cột gốc | Mô tả ngắn | Nguồn |
|---|---|---|---|---|
| `claim_id` | string | — | ID nội bộ `CLM_000001...`, dùng truy vết | Engineered |
| `source_row` | int64 | — | Số dòng tương ứng trong Excel nguồn | Engineered |
| `months_as_customer` | int64 | `months_as_customer` | Số tháng khách hàng gắn với doanh nghiệp | Original |
| `age` | int64 | `age` | Tuổi người được bảo hiểm | Original |
| `policy_number` | int64 | `policy_number` | Mã hợp đồng; identifier, không dùng làm feature | Original |
| `policy_bind_date` | datetime64 | `policy_bind_date` | Ngày hợp đồng bắt đầu hiệu lực | Original |
| `policy_state` | string | `policy_state` | Bang phát hành hợp đồng | Original |
| `policy_csl` | string | `policy_csl` | Mức giới hạn trách nhiệm kết hợp của hợp đồng | Original |
| `policy_deductable` | int64 | `policy_deductable` | Mức khấu trừ; giữ chính tả của nguồn | Original |
| `policy_annual_premium` | float64 | `policy_annual_premium` | Phí bảo hiểm năm | Original |
| `umbrella_limit` | int64 | `umbrella_limit` | Hạn mức bảo hiểm bổ sung | Original |
| `insured_zip` | int64 | `insured_zip` | Mã ZIP; proxy địa lý, đã loại khỏi model | Original |
| `insured_sex` | string | `insured_sex` | Giới tính khai báo | Original |
| `insured_education_level` | string | `insured_education_level` | Trình độ học vấn | Original |
| `insured_occupation` | string | `insured_occupation` | Nghề nghiệp | Original |
| `insured_hobbies` | string | `insured_hobbies` | Sở thích; proxy cần xem xét, đã loại trong một sensitivity check | Original |
| `insured_relationship` | string | `insured_relationship` | Quan hệ của người được bảo hiểm với chủ hợp đồng | Original |
| `capital_gains` | int64 | `capital-gains` | Giá trị capital gains trong dữ liệu nguồn | Original, renamed |
| `capital_loss` | int64 | `capital-loss` | Giá trị capital loss trong dữ liệu nguồn | Original, renamed |
| `incident_date` | datetime64 | `incident_date` | Ngày xảy ra sự cố | Original |
| `incident_type` | string | `incident_type` | Loại sự cố | Original |
| `collision_type` | string | `collision_type` | Loại va chạm; 178 giá trị thiếu | Original |
| `incident_severity` | string | `incident_severity` | Mức độ nghiêm trọng khai báo/đánh giá | Original |
| `authorities_contacted` | string | `authorities_contacted` | Cơ quan chức năng được liên hệ; 91 thiếu | Original |
| `incident_state` | string | `incident_state` | Bang xảy ra sự cố | Original |
| `incident_city` | string | `incident_city` | Thành phố xảy ra sự cố | Original |
| `incident_location` | string | `incident_location` | Địa điểm chi tiết; cardinality cao, đã loại | Original |
| `incident_hour_of_the_day` | int64 | `incident_hour_of_the_day` | Giờ xảy ra sự cố, 0–23 | Original |
| `number_of_vehicles_involved` | int64 | `number_of_vehicles_involved` | Số xe liên quan | Original |
| `property_damage` | string | `property_damage` | Có thiệt hại tài sản hay không; 360 thiếu | Original |
| `bodily_injuries` | int64 | `bodily_injuries` | Số người bị thương | Original |
| `witnesses` | int64 | `witnesses` | Số nhân chứng | Original |
| `police_report_available` | string | `police_report_available` | Có báo cáo cảnh sát hay không; 343 thiếu | Original |
| `total_claim_amount` | int64 | `total_claim_amount` | Tổng tiền claim; bằng tổng ba component trên 100% train | Original |
| `injury_claim` | int64 | `injury_claim` | Phần claim cho thương tích | Original |
| `property_claim` | int64 | `property_claim` | Phần claim cho tài sản | Original |
| `vehicle_claim` | int64 | `vehicle_claim` | Phần claim cho xe | Original |
| `auto_make` | string | `auto_make` | Hãng xe | Original |
| `auto_model` | string | `auto_model` | Model xe; Silver ép string để tránh mixed type | Original |
| `auto_year` | int64 | `auto_year` | Năm sản xuất xe | Original |
| `fraud_reported` | string | `fraud_reported` | Nhãn gốc Y/N; không dùng làm feature | Original target |
| `fraud_label` | Int64 | — | Nhãn số: Y→1, N→0 | Engineered target |

Rubric và đánh giá stage/reliability cho đủ 39 cột nguồn đã được lập tại `reports/LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md`; bản máy đọc nằm tại `configs/layer_b_field_governance_v1.csv`. Các dòng stage-confidence Thấp vẫn cần nghiệp vụ xác nhận trước pilot.
