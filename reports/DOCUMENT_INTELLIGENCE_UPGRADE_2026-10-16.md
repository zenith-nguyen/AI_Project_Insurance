# Nâng cấp đọc hiểu chứng từ, quan hệ và vận hành — 2026-10-16

## Phần đã triển khai

- Document pipeline v3 đánh giá độ đọc được sau OCR và phân luồng `printed_likely`, `mixed_or_uncertain`, `handwriting_or_low_quality_review` hoặc `no_text`.
- Kết quả chữ viết tay chỉ là cảnh báo định tuyến. Hệ thống chưa tuyên bố có model nhận dạng chữ viết tay bảo hiểm Việt Nam nếu chưa có benchmark đúng miền.
- Workbench hiển thị lý do, hành động cần làm, độ tin cậy OCR và giới hạn của kết quả.
- Registry chứng từ Việt Nam lưu phiên bản, ngày hiệu lực, ngày kiểm tra gần nhất, hạn kiểm tra tiếp theo và nguồn chính thức.
- Quan hệ hiển thị từng claim liên quan, loại thực thể, giá trị đã che, số claim cùng dùng và khoảng thời gian trước claim hiện tại.
- Job nền có vị trí hàng đợi, số worker, giới hạn lịch sử và endpoint vận hành để theo dõi khả năng xử lý.

## Cập nhật quy định/chứng từ

Nguồn giám sát hiện tại là Cơ sở dữ liệu Quốc gia về văn bản pháp luật và Hệ thống văn bản Chính phủ. Script `scripts/check_document_policy_sources.py` chỉ kiểm tra khả năng truy cập và dấu thay đổi của nguồn. Nó không tự sửa rule, không tự tuyên bố một chứng từ hợp lệ và không tự đưa ra quyết định bồi thường.

Quy trình cập nhật bắt buộc:

1. chạy source monitor theo lịch;
2. người phụ trách nghiệp vụ/pháp chế xem văn bản mới, hiệu lực và văn bản thay thế;
3. cập nhật YAML thành version mới và ghi người duyệt;
4. chạy regression test trên golden claims;
5. phát hành sau sign-off.

## Giá trị nghiệp vụ

- Chữ khó đọc được đưa tới đúng thao tác xác nhận thay vì âm thầm trả trường rỗng.
- Người duyệt biết rule chứng từ đã được rà soát khi nào và nguồn nào phải kiểm tra.
- Quan hệ trở thành danh sách đối chiếu cụ thể thay vì bốn con số NetworkX khó hiểu.
- Hàng đợi cho biết hồ sơ đang chờ hay đang chạy, giúp người dùng không bấm phân tích lặp lại.

## Giới hạn và mốc tiếp theo

- Cần 50–100 trang chứng từ thật có quyền sử dụng, gồm riêng chữ in, chữ viết tay và tài liệu hỗn hợp.
- Cần gán nhãn dòng chữ, trường nghiệp vụ và thời gian chỉnh sửa của người duyệt.
- Chỉ bật model handwriting chuyên dụng sau khi field accuracy, correction time và false-fill rate đạt ngưỡng đã khóa.
- Scale pilot cần durable queue, worker process tách biệt, object storage/database có xác thực và monitoring; thread pool local chỉ phù hợp demo/research.
