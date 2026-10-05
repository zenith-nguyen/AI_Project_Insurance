# Feature-policy validation trên `val_fs`

Mỗi profile dùng cùng cấu hình XGBoost, fit trên `train_fs` và đánh giá trên `val_fs`. Script không đọc test 200 dòng đã dùng hai lần trước đó. Đây là bằng chứng để chọn feature, không phải ước lượng hiệu năng cuối cùng.

| Profile | Số feature | AP | ROC-AUC | Recall@10% | Recall@20% |
|---|---:|---:|---:|---:|---:|
| `research_full` | 29 | 0.670 | 0.850 | 28.6% | 54.3% |
| `bias_excluded_current` | 28 | 0.598 | 0.786 | 25.7% | 48.6% |
| `stage1_intake` | 10 | 0.267 | 0.540 | 8.6% | 14.3% |
| `stage3_complete` | 19 | 0.500 | 0.772 | 22.9% | 42.9% |

`research_full` giữ nhóm proxy để làm mốc nghiên cứu; `bias_excluded_current` bỏ `insured_hobbies`, `insured_zip` và `incident_location`; hai profile theo stage vẫn là ứng viên cho đến khi nghiệp vụ xác nhận thời điểm có sẵn của từng trường.

Không dùng bảng này để tuyên bố production readiness. Sau khi chốt feature policy và model, cần một external test mới cho đánh giá cuối cùng.
