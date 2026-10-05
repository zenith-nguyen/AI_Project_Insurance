# Kiểm tra độ nhạy theo nhóm feature

Đây là phân tích thăm dò bằng CV chỉ trên train; không dùng nhãn validation/test và không thay đổi kết quả test đã chốt.

| Nhóm feature | Average Precision CV trung bình | Recall@10% CV trung bình | Số cột đầu vào |
|---|---:|---:|---:|
| Mô hình nghiên cứu hiện tại | 0.706 | 0.303 | 28 |
| stage1_intake | 0.284 | 0.105 | 10 |
| stage3_complete | 0.506 | 0.236 | 19 |

SHAP của mô hình hiện tại bị chi phối bởi nhóm sở thích. Số lượng trên train dưới đây cho thấy cần kiểm tra nguồn gốc tín hiệu; đây không phải quan hệ nhân quả:

- `cross-fit`: 21 nhãn fraud và 2 nhãn non-fraud trong 23 dòng train.
- `chess`: 28 nhãn fraud và 5 nhãn non-fraud trong 33 dòng train.

`stage1_intake` chỉ dùng thông tin hợp đồng/xe và sự cố cơ bản. `stage3_complete` thêm thông tin từ hồ sơ đã hoàn chỉnh nhưng bỏ sở thích, nhân khẩu học, nghề nghiệp, vốn và địa lý. Nhóm vẫn phải xác nhận từng trường có sẵn tại thời điểm chấm điểm hay không.

Kết luận: giữ mô hình ban đầu làm baseline nghiên cứu. Hai nhóm theo giai đoạn là ứng viên thăm dò, chưa đủ cơ sở để ra quyết định tự động. Cần xác nhận thời điểm có dữ liệu, nguồn gốc nhãn và ảnh hưởng theo nhóm khách hàng.
