# Cập nhật dự án phát hiện gian lận bảo hiểm

**Ngày cập nhật:** 06/10/2026  
**Mục đích:** Tóm tắt để cả nhóm nắm được việc đã làm, kết quả hiện tại, vấn đề đang gặp và kế hoạch tiếp theo.

## 1. Tình hình chung

Dự án hiện có hai nhánh độc lập:

1. **Nhánh dữ liệu hồ sơ:** chấm điểm rủi ro gian lận để nhân viên ưu tiên kiểm tra hồ sơ.
2. **Nhánh ảnh CarDD:** nhận diện và phân vùng sáu loại hư hại trên xe.

Nhánh hồ sơ đã có mô hình thử nghiệm và số liệu đánh giá. Nhánh CarDD đã hoàn tất kiểm tra dữ liệu và chuyển đổi nhãn, nhưng **chưa huấn luyện mô hình ảnh**. Google Drive hiện hết dung lượng vì bộ ảnh bị lưu trùng trong Bronze và Processed; nhóm đã có phương án dọn an toàn nhưng chưa chạy xong trên Drive.

## 2. Những việc đã hoàn thành

### Nhánh hồ sơ gian lận

- Đã xử lý 1.000 hồ sơ, gồm 753 hồ sơ non-fraud và 247 hồ sơ fraud.
- Đã xây dựng quy trình Bronze → Silver → Gold, kiểm tra dữ liệu thiếu, loại identifier và kiểm tra leakage.
- Đã so sánh Logistic Regression, Random Forest, XGBoost và LightGBM bằng cross-validation trên train.
- XGBoost được chọn vì có Average Precision CV cao nhất: **0,706**.
- Mô hình chỉ tạo điểm rủi ro để hỗ trợ người kiểm tra; không tự kết luận gian lận hoặc tự từ chối bồi thường.

Kết quả trên frozen test 200 hồ sơ:

| Chỉ số | XGBoost | Rule baseline |
|---|---:|---:|
| Average Precision | 0,559 | 0,424 |
| ROC-AUC | 0,825 | 0,721 |
| Recall@10% | 22,4% | 16,3% |
| Precision@10% | 55,0% | 40,0% |
| Recall@20% | 44,9% | 24,5% |
| Precision@20% | 55,0% | 30,0% |

Mô hình tốt hơn rule ở Recall@10% khoảng **6,1 điểm phần trăm**, nhưng chưa đạt mục tiêu đề xuất tăng 10 điểm phần trăm.

### Kiểm tra feature có nguy cơ bias

- Một số giá trị của `insured_hobbies` xuất hiện cao trong SHAP, nhưng bỏ riêng trường này chỉ làm kết quả thay đổi nhỏ và trái chiều.
- Khi bỏ cả nhóm thông tin có thể đóng vai trò proxy như nhân khẩu học, địa lý, sở thích, nghề nghiệp và vốn, CV Average Precision giảm từ **0,706 xuống khoảng 0,506**.
- Vì vậy, rủi ro nằm ở **nhóm proxy rộng**, không có cơ sở nói rằng sở thích cá nhân là dấu hiệu gian lận thật.
- Frozen test đã được dùng hai lần cho so sánh feature policy. Từ nay các quyết định feature dùng `train_fs` 560 dòng và `val_fs` 140 dòng; sau khi chốt mô hình cần một test bên ngoài mới.

### Nhánh ảnh CarDD

- Lần tải đầu có 2.753 ảnh nhưng annotation tham chiếu 2.816 ảnh. Đã tìm và tải bù đúng 63 ảnh thiếu.
- Kiểm tra cuối có **2.816 ảnh khớp 2.816 sample**, không có ảnh thiếu, ảnh thừa hoặc ảnh hỏng.
- Dataset có **6.211 vùng hư hại thực**, thuộc sáu lớp: `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`.
- Đã giải mã đúng mask FiftyOne và chuyển sang định dạng YOLO segmentation.
- Conversion v2 dùng seed cố định `20261006` và tạo:

| Split | Số ảnh |
|---|---:|
| Train | 1.966 |
| Validation | 431 |
| Test | 419 |

Phân bố từng lớp gần tỷ lệ 70/15/15. Một cặp ảnh gần trùng được giữ trong cùng split để tránh rò rỉ giữa train và test.

## 3. Vấn đề dung lượng Google Drive

### Nguyên nhân

Ảnh CarDD đang tồn tại hai lần:

- Bản gốc trong `data/bronze/layerA_cardd/data`.
- Bản copy trong `data/processed/cardd_yolo_v1/images`.

Vì Drive chạm quota, Colab không thể ghi thêm report/script và notebook không tự lưu ổn định.

### Phương án xử lý đã chuẩn bị

1. Tải notebook hiện tại về máy để tránh mất nội dung chưa lưu.
2. Kiểm tra tự động rằng Bronze còn đủ 2.816 ảnh, Processed còn đủ 2.816 label và manifest còn đủ 2.816 dòng.
3. Chỉ xóa thư mục ảnh copy trong Processed; không xóa Bronze, labels, manifest hoặc report.
4. Dọn các file vừa xóa khỏi Google Drive Trash để quota thực sự được giải phóng.
5. Khi huấn luyện, dựng một dataset YOLO tạm trong `/content` bằng liên kết tới Bronze. Bản tạm không chiếm thêm dung lượng Drive và tự mất khi Colab kết thúc.

**Trạng thái hiện tại:** code cleanup đã qua kiểm thử local; thao tác cleanup trên Google Drive vẫn chưa hoàn tất.

## 4. Các giới hạn cần nói rõ

- Tỷ lệ fraud của dataset là 24,7%, cao hơn nhiều so với giả định production 5–10%. Kết quả hiện tại chưa đại diện cho môi trường thực tế.
- Với tỷ lệ fraud hiện tại, Recall@10% tối đa về mặt toán học chỉ khoảng 40,5–40,8%; mục tiêu 60% không thể đánh giá trực tiếp trên dataset này.
- Nguồn gốc và quy trình xác lập nhãn `fraud_reported` chưa được kiểm chứng.
- CarDD, dữ liệu Kaggle và dữ liệu chứng từ chưa có `claim_id` chung, nên chưa thể gọi đây là mô hình multimodal cho cùng một hồ sơ.
- License CarDD yêu cầu prior consent của PIC Lab cho mục đích nghiên cứu. Repo chưa có bằng chứng consent, vì vậy không chia sẻ raw data hoặc bắt đầu training trước khi lưu xác nhận quyền sử dụng.
- Chưa có chi phí review, SIU, false hold và fraud loss thực tế, nên chưa tính Net Value và chưa tuyên bố sẵn sàng production.

## 5. Kế hoạch tiếp theo

| Ưu tiên | Việc cần làm | Kết quả mong đợi |
|---|---|---|
| 1 | Dọn bản ảnh CarDD bị copy trùng và làm trống Drive Trash | Drive có lại dung lượng; notebook lưu được |
| 2 | Dựng dataset YOLO tạm trong `/content` và chạy validator v2 | Xác nhận dataset dùng để train hợp lệ |
| 3 | Lưu bằng chứng prior consent của PIC Lab | Đủ điều kiện dùng CarDD cho đồ án |
| 4 | Huấn luyện baseline YOLOv8-seg trên train, chọn checkpoint bằng validation | Có kết quả nhánh ảnh lần đầu |
| 5 | Chỉ đánh giá test sau khi đã chốt model | Tránh dùng test để điều chỉnh mô hình |
| 6 | Xác nhận thời điểm có sẵn của các feature và provenance của nhãn fraud | Hoàn thiện chính sách feature cho hai giai đoạn chấm điểm |

## 6. Nội dung cần nhóm thống nhất

- Thống nhất rằng kết quả tabular hiện là **research baseline hỗ trợ xếp hạng**, không phải hệ thống tự quyết định.
- Cung cấp hoặc lưu bằng chứng quyền sử dụng CarDD.
- Xác nhận feature nào có sẵn lúc tiếp nhận hồ sơ và feature nào chỉ có sau khi hồ sơ hoàn chỉnh.
- Nếu muốn đánh giá hiệu quả tài chính, nhóm cần cung cấp chi phí review, SIU, false hold và tổn thất fraud có thể tránh được.

## 7. Kịch bản trình bày ngắn

> Hiện dự án có hai nhánh. Nhánh thứ nhất dùng dữ liệu hồ sơ để xếp hạng rủi ro gian lận. Chúng ta đã xử lý 1.000 hồ sơ, so sánh bốn mô hình và chọn XGBoost. Trên tập test 200 hồ sơ, mô hình có Average Precision 0,559, ROC-AUC 0,825 và tìm được 22,4% số hồ sơ fraud khi chỉ kiểm tra 10% hồ sơ có điểm cao nhất. Kết quả tốt hơn rule hiện tại nhưng chưa đạt toàn bộ KPI đề xuất.
>
> Kiểm tra bias cho thấy không nên nói sở thích cá nhân là dấu hiệu gian lận. Kết quả cho thấy mô hình có thể đang dùng một nhóm proxy rộng gồm nhân khẩu học, địa lý, sở thích, nghề nghiệp và vốn. Vì tập test cũ đã được dùng hai lần, mọi quyết định feature tiếp theo sẽ dùng validation riêng; sau khi chốt mô hình cần test mới.
>
> Với nhánh ảnh, chúng ta đã sửa đủ 63 ảnh bị thiếu, xác minh 2.816 ảnh và 6.211 vùng hư hại, rồi chuyển thành YOLO segmentation với train, validation và test tách riêng. Mô hình ảnh chưa được train.
>
> Vấn đề hiện tại là Google Drive hết dung lượng vì ảnh CarDD bị lưu hai bản. Nhóm đã chuẩn bị cách kiểm tra rồi chỉ xóa bản copy trong Processed, giữ nguyên Bronze và labels. Sau khi giải phóng dung lượng và xác nhận quyền sử dụng CarDD, bước tiếp theo là validate lại dataset tạm và chạy baseline YOLOv8-seg.

## 8. Tài liệu chi tiết

- `reports/RESULTS.md`: kết quả nhánh tabular và giới hạn.
- `reports/FEATURE_POLICY.md`: so sánh feature trên validation riêng.
- `reports/handoff/model_card.md`: mô tả mô hình cho người không chuyên.
- `reports/handoff/cardd_summary.md`: trạng thái CarDD.
- `reports/handoff/risk_register_v2_additions.md`: các rủi ro mới.
