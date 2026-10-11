# Khắc phục data gate LayoutLMv3 v3

**Ngày cập nhật:** 11/10/2026  
**Trạng thái:** bản v2 dừng an toàn trước training; bản v3 đã sửa thuật toán căn chỉnh và chờ chạy trên Colab.

## Sự cố quan sát được

`Document_LayoutLMv3_Candidate_Acc2_v2.ipynb` báo weak-alignment coverage cho `date/total` bằng **0,1290**, thấp hơn ngưỡng khóa **0,85**. Đây là lỗi tương thích giữa thuật toán tạo nhãn BIO và schema dữ liệu, không phải lỗi checkpoint LayoutLMv3. Notebook đã dừng trước `trainer.train()`, không đọc test và không tạo model candidate sai.

Mirror `jsdnrs/ICDAR2019-SROIE` lưu phần tử `words` theo dòng OCR. Một token có thể là `25/12/2018 8:13:39 PM`, trong khi entity ground truth chỉ là `25/12/2018`. OCR cũng có sai khác ký tự. Phép so khớp tuyệt đối của v2 vì thế bỏ sót nhãn hợp lệ.

## Bản sửa v3

Notebook mới: `Document_LayoutLMv3_Candidate_Acc2_v3.ipynb`.

- Giới hạn candidate vào hai trường `date` và `total`, đúng phạm vi rule baseline dùng để so sánh.
- Chuẩn hóa ngày về giá trị lịch, hỗ trợ `YYYYMMDD` và `DD/MM/YYYY`.
- Chuẩn hóa số tiền bằng `Decimal`, hỗ trợ dấu phẩy/dấu chấm.
- Dùng từ `DATE`/`TOTAL` trong ngữ cảnh để phá hòa giữa nhiều giá trị giống nhau; ngữ cảnh không thể tự tạo một match.
- Chỉ dùng fuzzy match khi điểm độc lập đạt ít nhất 0,84.
- In số lượng, phương thức match và tối đa 10 mẫu không match trước training.
- Giữ nguyên cổng coverage 0,85 và mức cải thiện F1 tối thiểu 0,02.

Kiểm tra phát triển trên 100 hàng đầu từ đúng mirror cho kết quả **183/183 entity date/total được căn chỉnh**. Đây là kiểm tra thuật toán, chưa thay cho output validation trên processed split 93 hàng của nhóm.

## Cách chạy

1. Mở bản v3 mới và chọn GPU runtime.
2. Chạy tuần tự từ đầu; không tiếp tục notebook v1/v2 đã mở trong tab cũ.
3. Ở cell căn chỉnh, chỉ tiếp tục khi có `Weak-alignment coverage (date/total)` từ 0,85 trở lên.
4. Gửi toàn bộ output gồm alignment counts, alignment methods, metric validation, quyết định chọn candidate và đường dẫn report.
5. Test split vẫn khóa. Chưa tạo notebook final test KIE trước khi review validation.

