# Thiết kế lại sản phẩm theo giá trị nghiệp vụ v1

Ngày cập nhật: 14/10/2026

## 1. Sản phẩm dành cho ai và giải quyết việc gì?

Sản phẩm là **Claim Review Workbench** dành cho nhân viên tiếp nhận, giám định và điều tra hồ sơ bồi thường. Hệ thống gom dữ liệu khai báo, ảnh xe, chứng từ và quan hệ giữa các hồ sơ để trả lời bốn câu hỏi:

1. Hồ sơ này nên được xem ở mức ưu tiên nào?
2. Hệ thống đã phát hiện điều gì và dựa trên bằng chứng nào?
3. Phát hiện đó có ý nghĩa gì với người duyệt?
4. Người duyệt nên làm gì tiếp theo?

Đây là công cụ hỗ trợ rà soát. Điểm rủi ro hoặc tín hiệu từ một model không tự động kết luận gian lận và không tự động từ chối bồi thường.

## 2. Luồng mới dành cho người dùng

Người dùng chỉ cần:

1. nhập một vài thông tin họ biết, như số tiền yêu cầu, ngày sự cố và biển số;
2. chọn ảnh xe và chứng từ;
3. bấm **Phân tích hồ sơ**;
4. đọc phần **phát hiện → ý nghĩa → hành động**;
5. ghi quyết định hoặc yêu cầu bổ sung bằng chứng.

Người dùng nghiệp vụ không phải nhập JSON, chọn model, gọi endpoint hoặc hiểu checkpoint. Trong bản demo, nút **Dùng hồ sơ mẫu** nạp kín các feature kỹ thuật để trình diễn XGBoost. Khi tích hợp thật, backend lấy các trường này từ core insurance/claim system.

Hệ thống vẫn trả kết quả một phần nếu thiếu ảnh, chứng từ hoặc graph. Mỗi phần thiếu được ghi là **chưa đánh giá được**; hệ thống không chuyển phần thiếu thành điểm an toàn bằng 0.

## 3. Technical value phải dẫn đến business value

| Đầu ra kỹ thuật | Câu hỏi nghiệp vụ | Cách hiển thị cho người duyệt | Hành động có thể thực hiện | Giới hạn phải nói rõ |
| --- | --- | --- | --- | --- |
| XGBoost risk ranking | Hồ sơ nào nên xem trước? | Mức ưu tiên hàng đợi và các tín hiệu chính | Ưu tiên rà soát hoặc xử lý theo luồng thường | Điểm nghiên cứu, chưa phải xác suất gian lận đã hiệu chuẩn |
| YOLO damage segmentation | Hư hỏng nằm ở đâu và thuộc nhóm nào? | Ảnh có vùng khoanh, tên hư hỏng và độ tin cậy | Đối chiếu lời khai, yêu cầu góc ảnh bổ sung | Module chưa chạy nếu thiếu checkpoint; lớp crack/dent/scratch còn yếu |
| DiT + OCR + LayoutLMv3 | Chứng từ loại gì, ngày và số tiền là gì? | Trường trích xuất cạnh vùng chứng từ nguồn | Sửa trường sai hoặc đối chiếu với claim | OCR còn sai; LayoutLMv3 hiện chỉ được kiểm thử chính trên date/total của SROIE |
| Consistency rules | Dữ liệu giữa claim và chứng từ có lệch không? | Nêu hai giá trị, mức chênh và quy tắc | Xác minh hoặc yêu cầu chứng từ bổ sung | Chỉ chạy khi có đủ hai vế để so sánh |
| NetworkX | Thực thể nào xuất hiện ở nhiều claim? | Quan hệ, số claim liên quan và thời điểm | Chuyển SIU khi có bằng chứng đủ mạnh | Thiếu entity/edge thì trả không đủ dữ liệu, không suy ra an toàn |
| Media authenticity | Có bằng chứng về nguồn gốc, chỉnh sửa hoặc tái sử dụng ảnh không? | Nêu marker/credential/hash trùng và ý nghĩa | Yêu cầu ảnh gốc, chụp hướng dẫn hoặc kiểm tra thủ công | Không có marker không chứng minh ảnh thật; chưa có pixel detector đã hiệu chuẩn |

## 4. Phát hiện ảnh AI: trạng thái đúng hiện tại

Module hiện có giá trị ở vai trò **kiểm tra tính xác thực của bằng chứng**, gồm:

- đọc EXIF/XMP và dấu hiệu phần mềm tạo/chỉnh sửa;
- xác minh Content Credentials/C2PA khi công cụ và credential có sẵn;
- ghi nhận marker AI được khai báo nếu tìm thấy;
- phát hiện cùng ảnh hoặc ảnh gần giống đã xuất hiện ở claim khác;
- hỗ trợ phiên chụp hướng dẫn để giảm rủi ro dùng ảnh có sẵn.

Module chưa đủ cơ sở để tuyên bố phát hiện mọi ảnh AI. Ảnh có thể bị chụp lại màn hình, nén qua mạng xã hội, xóa metadata hoặc được tạo bởi generator chưa thấy trong tập huấn luyện. Vì vậy kết quả mặc định là **chưa đủ bằng chứng xác định ảnh AI**, kèm lý do và bước kiểm tra tiếp theo.

Để bổ sung pixel-forensics có giá trị, cần một benchmark đúng miền gồm ảnh camera gốc, ảnh chỉnh sửa thông thường, ảnh qua Facebook/TikTok, ảnh chụp lại màn hình và nhiều họ generator AI. Threshold phải khóa trên validation, sau đó đo test theo từng generator và từng biến đổi. Chỉ bật nhãn cảnh báo trong sản phẩm khi đạt precision đủ cao để không gây giữ nhầm hồ sơ.

## 5. KPI sản phẩm

Không đánh giá sản phẩm chỉ bằng F1 hoặc mAP. Pilot cần đo song song:

| Nhóm | KPI kỹ thuật | KPI nghiệp vụ đi kèm |
| --- | --- | --- |
| Triage | Recall@10%, PR-AUC, calibration | Thời gian duyệt trung bình, tỷ lệ hồ sơ ưu tiên có phát hiện hữu ích, false hold |
| Hư hỏng | mAP/IoU theo lớp | Tỷ lệ vùng khoanh được GĐV chấp nhận, số ảnh phải yêu cầu chụp lại |
| Chứng từ | CER/WER, field F1 | Tỷ lệ trường phải sửa, thời gian nhập liệu tiết kiệm, tỷ lệ đối chiếu thành công |
| Quan hệ | precision/recall của link | Tỷ lệ link được SIU xác nhận hữu ích |
| Authenticity | precision/recall theo loại biến đổi | Tỷ lệ cảnh báo đúng, tỷ lệ yêu cầu ảnh gốc hợp lý, false escalation |
| Toàn hệ thống | latency, error rate, module coverage | Thời gian xử lý claim, tỷ lệ hồ sơ hoàn tất, mức hài lòng/UAT |

## 6. Definition of Done cho bản pilot

Bản pilot chỉ được coi là hoàn thành khi:

- người dùng tạo và phân tích claim mà không nhập JSON;
- một `claim_id` nối xuyên suốt dữ liệu bảng, ảnh, chứng từ, graph và audit log;
- UI luôn cho biết phần nào đã chạy, phần nào thiếu dữ liệu hoặc artifact;
- mọi phát hiện có bằng chứng, ý nghĩa nghiệp vụ, hành động đề xuất và giới hạn;
- YOLO và document pipeline chạy bằng checkpoint đã đăng ký, kiểm tra hash thành công;
- ảnh hư hỏng có overlay khi model trả detection;
- người duyệt sửa được OCR/KIE và lưu quyết định vào audit trail;
- golden claims chạy end-to-end ổn định;
- benchmark authenticity, dữ liệu bảo hiểm Việt Nam, privacy/security, load test và UAT đạt ngưỡng đã khóa;
- có monitoring, versioning và phương án rollback.

## 7. Trạng thái sau lần thiết kế lại này

Đã hoàn thành trong giao diện:

- bỏ ô JSON khỏi luồng người dùng;
- gom thao tác thành một nút **Phân tích hồ sơ**;
- tự chạy các module khả dụng và cho phép kết quả một phần;
- chuyển trọng tâm trang kết quả sang hướng xử lý, phát hiện, ý nghĩa và việc cần làm;
- đưa model/version/confidence vào vùng chi tiết kỹ thuật;
- diễn giải authenticity theo bằng chứng và hiển thị trạng thái không kết luận khi chưa đủ dữ liệu;
- nói rõ YOLO/document model chưa chạy khi thiếu checkpoint, thay vì khiến người dùng hiểu là không có hư hỏng hoặc chứng từ hợp lệ.

Phần còn phải làm để đạt pilot là kết nối artifact live cho YOLO và document pipeline, thu thập benchmark authenticity, bổ sung correction workflow, đánh giá dữ liệu Việt Nam và thực hiện UAT.
