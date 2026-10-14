# Media authenticity and relationship matching v3

Ngày khóa tài liệu: 2026-10-14.

## Người dùng nhìn thấy gì

Khi bấm **Phân tích hồ sơ**, backend tự chạy các kiểm tra nguồn gốc ảnh và quan hệ. Người dùng không cần gọi endpoint authenticity riêng và không cần nhập feature JSON. Endpoint riêng chỉ phục vụ đội kỹ thuật xem lại một báo cáo đã tạo.

Workbench trả lời bốn câu hỏi nghiệp vụ:

1. File có Content Credentials/C2PA hoặc metadata khai báo nội dung AI không?
2. Metadata có khai báo phần mềm chỉnh sửa như Photoshop, Lightroom, GIMP, Snapseed, PicsArt, Canva hoặc Luminar không?
3. Ảnh có trùng nguyên byte hoặc gần trùng với ảnh ở claim trước dù bị xoay, resize hay nén lại không?
4. Claim có dùng chung biển số, số điện thoại hoặc xưởng sửa chữa với claim đã tồn tại trước thời điểm chấm không?

Kết quả luôn kèm hành động đề xuất. Các tín hiệu này hỗ trợ ưu tiên rà soát; chúng không tự kết luận gian lận.

## Thay đổi kỹ thuật v3

- `media_authenticity_v3` tách marker AI và marker phần mềm chỉnh sửa.
- Perceptual matching dùng dHash cho bốn góc xoay, center crop, khoảng cách màu và SHA-256 cho bản trùng tuyệt đối.
- Runtime intake nhận `relationship_entities` gồm dữ liệu như `contact_phone` và `repair_shop`.
- NetworkX dựng graph theo thời điểm; giá trị thực thể được chuẩn hóa và băm trước khi đưa vào node ID.
- API trả thêm `related_claim_ids` và `shared_entity_types` để UI diễn giải cụ thể hồ sơ nào và loại dữ liệu nào trùng.
- UI intake có trường số điện thoại và xưởng sửa chữa tùy chọn; UI graph hiển thị hồ sơ liên quan thay vì chỉ hiện bốn con số.
- Có adapter pixel forensic tùy chọn qua `INSURANCE_FORENSIC_CHECKPOINT` và `INSURANCE_FORENSIC_CALIBRATION`. Adapter chỉ khởi động khi calibration manifest xác nhận model đã được hiệu chuẩn và kiểm thử trong miền bảo hiểm; output vẫn là tín hiệu sàng lọc.

## Giới hạn bắt buộc khi diễn giải

- Không thấy metadata, SynthID hay C2PA không chứng minh ảnh là ảnh camera gốc.
- Metadata thường có thể bị xóa hoặc giả mạo. C2PA cần kiểm tra chữ ký và trust policy.
- SynthID chỉ hữu ích với nội dung có watermark tương thích và detector/provider tương ứng.
- Ảnh AI không marker có thể vẫn cho kết quả `inconclusive` vì chưa có pixel-forensic model được hiệu chuẩn trên ảnh bảo hiểm.
- Ảnh bị AI sửa mạnh có thể không còn đủ giống để perceptual hash nối về ảnh gốc.
- Cùng số điện thoại/xưởng/biển số có thể hợp lệ; graph chỉ tạo tín hiệu điều tra.

## Bằng chứng kiểm thử

Các contract test bao phủ:

- bản ảnh trùng SHA-256;
- ảnh resize và nén lại được nhận là `near_duplicate`;
- metadata khai báo AI và Photoshop;
- hai claim dùng chung số điện thoại và xưởng tạo graph point-in-time;
- claim thiếu chứng từ vẫn giữ risk score nếu feature bảng đầy đủ.

Bộ demo thao tác tay nằm tại `D:\My Dowload\00_TEST_CLAIM_AI_RELATION_2026-10-14` và bản ZIP cùng tên. Chạy case theo thứ tự 01 đến 06 để quan hệ chỉ sử dụng dữ liệu đã xuất hiện trước đó.
