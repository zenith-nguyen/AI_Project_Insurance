# Kiểm tra độ nhạy theo nhóm feature

Đây là phân tích thăm dò bằng CV chỉ trên train; không dùng nhãn validation/test và không thay đổi kết quả test đã chốt.

| Nhóm feature | Average Precision CV trung bình | Recall@10% CV trung bình | Số cột đầu vào |
|---|---:|---:|---:|
| Mô hình nghiên cứu hiện tại | 0.706 | 0.303 | 29 |
| stage1_intake | 0.284 | 0.105 | 10 |
| stage3_complete | 0.506 | 0.236 | 19 |

Một số category sở thích đứng cao trong SHAP, nhưng không đủ để kết luận mô hình phụ thuộc chủ yếu vào riêng `insured_hobbies`. Khi bỏ riêng trường này trên frozen test, AP đổi +0,007, ROC-AUC -0,033, Recall@10% -2,0 điểm phần trăm và Recall@20% +2,0 điểm phần trăm. Mức giảm lớn xuất hiện khi bỏ cả nhóm proxy nhân khẩu học/địa lý/sở thích/nghề nghiệp/vốn: CV AP từ 0,706 xuống 0,506. Vì vậy phát hiện phù hợp hơn là sự phụ thuộc vào nhóm proxy rộng; các thống kê dưới đây chỉ giúp truy nguồn tín hiệu và không phải quan hệ nhân quả:

- `cross-fit`: 21 nhãn fraud và 2 nhãn non-fraud trong 23 dòng train.
- `chess`: 28 nhãn fraud và 5 nhãn non-fraud trong 33 dòng train.

`stage1_intake` chỉ dùng thông tin hợp đồng/xe và sự cố cơ bản. `stage3_complete` thêm thông tin từ hồ sơ đã hoàn chỉnh nhưng bỏ sở thích, nhân khẩu học, nghề nghiệp, vốn và địa lý. Nhóm vẫn phải xác nhận từng trường có sẵn tại thời điểm chấm điểm hay không.

Kết luận: giữ mô hình ban đầu làm baseline nghiên cứu. Hai nhóm theo giai đoạn là ứng viên thăm dò, chưa đủ cơ sở để ra quyết định tự động. Cần xác nhận thời điểm có dữ liệu, nguồn gốc nhãn và ảnh hưởng theo nhóm khách hàng.
