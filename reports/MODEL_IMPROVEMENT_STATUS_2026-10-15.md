# Trạng thái nâng cấp model và giá trị nghiệp vụ

Cập nhật: 2026-10-15. Mục tiêu phát hành: `research_handoff`.

Hệ thống đã chạy được lát cắt local end-to-end và các adapter model thật. Chất lượng production chưa được xác nhận vì còn thiếu bộ dữ liệu bảo hiểm Việt Nam có nhãn và sign-off nghiệp vụ.

> Quy ước: “Đã xong phần kỹ thuật” chỉ xác nhận pipeline/safeguard đã có kiểm thử. Production readiness còn cần validation đúng miền, security và UAT.

| # | Hạng mục | Trạng thái | Bằng chứng/metric hiện tại | Giá trị nghiệp vụ | Đang thiếu |
|---:|---|---|---|---|---|
| 1 | Golden claims end-to-end | Đang triển khai/đánh giá | Binary gate 6/6 PASS; 4 damage regions; 1 document result; CPU analysis 144.7s | Chứng minh một hồ sơ đi xuyên suốt từ nạp dữ liệu, phân tích, xem bằng chứng, sửa trường đến lưu quyết định mà không mất liên kết. | Thiếu 20–50 claim đúng miền và business sign-off |
| 2 | PaddleOCR trên chứng từ Việt Nam | Chờ dữ liệu đúng miền | CER 0.4097; WER 0.5592 | Tự điền ngày, tổng tiền và biển số để giảm nhập tay; confidence thấp vẫn chuyển người duyệt xác nhận. | Chưa có validation set chứng từ bảo hiểm Việt Nam có ground truth |
| 3 | XGBoost xếp hạng hồ sơ | Đang triển khai/đánh giá | Frozen test AP 0.559; Recall@10% 22.4%; val_fs best research AP 0.670 | Xếp claim cần xem trước trong cùng năng lực xử lý; điểm không phải xác suất gian lận và không tự từ chối bồi thường. | Chưa có feature S1–S5 claim-linked và chi phí nghiệp vụ để tính Net Value |
| 4 | YOLOv8s-seg hư hỏng đúng miền | Chờ dữ liệu đúng miền | Final mask mAP50–95 0.5140 | Khoanh vùng vị trí cần giám định và đối chiếu với mô tả/báo giá, giúp người duyệt tập trung vào vùng ảnh liên quan. | Chưa có ảnh hư hỏng bảo hiểm Việt Nam được gắn mask và cấp phép |
| 5 | DiT và LayoutLMv3 trên chứng từ bảo hiểm Việt Nam | Chờ dữ liệu đúng miền | DiT macro-F1 0.9283; LayoutLMv3 field F1 0.8659 | Phân loại đúng chứng từ và trích trường quan trọng để tự đối chiếu hồ sơ, đồng thời đưa trường confidence thấp cho người duyệt sửa. | Chưa có taxonomy và bộ chứng từ Việt Nam có nhãn |
| 6 | Consistency rules và NetworkX | Đang triển khai/đánh giá | Engineering contract tests PASS; chưa có precision nghiệp vụ | Nêu rõ thông tin không khớp và mở rộng điều tra sang claim dùng chung biển số, điện thoại hoặc xưởng trước thời điểm chấm. | Chưa có case lịch sử đã xác minh và rule sign-off |
| 7 | Benchmark nguồn gốc và chỉnh sửa ảnh | Đang triển khai/đánh giá | Engineering contract tests PASS; chưa có domain precision/recall | Tìm bằng chứng tái sử dụng hoặc dấu chỉnh sửa để yêu cầu ảnh tốt hơn mà không cáo buộc nhầm khách hàng là gian lận. | Chưa có benchmark ảnh bảo hiểm đa nguồn được cấp phép |
| 8 | Pixel forensic detector có calibration gate | Đã xong phần kỹ thuật | Gate implemented; detector not promoted | Tránh biến heuristic yếu thành kết luận ảnh AI; người duyệt nhận lý do và hành động thu thập bằng chứng thay thế. | Không có; safeguard đã hoạt động, model vẫn chờ benchmark |
| 9 | UI diễn giải technical value thành hành động nghiệp vụ | Đã xong phần kỹ thuật | Automated UI/API contract tests PASS | Người dùng thấy hệ thống phát hiện gì, vì sao cần quan tâm, việc nên làm tiếp, phần nào chưa kiểm tra và quyết định nào đã lưu. | Chưa có UAT và sign-off người dùng nghiệp vụ |

## Chi tiết gate và việc tiếp theo

### 01. Golden claims end-to-end

- **Bằng chứng kỹ thuật:** Có 5 golden claims xác định; golden nhị phân tổng hợp đã PASS 6/6 module, audit replay và traceability. Sign-off nghiên cứu chưa đạt vì bộ 20–50 claim đúng miền cùng expected action chưa được nghiệp vụ duyệt.
- **KPI nghiệp vụ:** Tỷ lệ chạy đủ module; thời gian xử lý; correction rate; audit replay
- **Điều kiện đạt:** 20–50 claim, không lỗi im lặng, expected action được nghiệp vụ ký duyệt
- **Việc tiếp theo:** Thu thập và ẩn danh bộ claim đa phương thức; chạy strict golden gate

### 02. PaddleOCR trên chứng từ Việt Nam

- **Bằng chứng kỹ thuật:** Baseline SROIE: CER 40,97%; document adapter đã nối live
- **KPI nghiệp vụ:** Field accuracy trọng yếu; correction rate; thời gian đọc/chứng từ
- **Điều kiện đạt:** Validation tiếng Việt tách biệt; business field accuracy và latency đạt ngưỡng đã khóa
- **Việc tiếp theo:** Gắn nhãn chứng từ Việt Nam; benchmark orientation, deskew, crop, contrast và OCR tiếng Việt

### 03. XGBoost xếp hạng hồ sơ

- **Bằng chứng kỹ thuật:** Model v1 đã khóa test; feature-policy đã so sánh trên train_fs/val_fs mà không đọc lại frozen test.
- **KPI nghiệp vụ:** Recall@K; precision trong queue; false hold; Net Value
- **Điều kiện đạt:** Feature đúng thời điểm, nhãn đáng tin, external test mới và Net Value không giảm
- **Việc tiếp theo:** Liên kết S1–S5 theo claim_id trên train_fs/val_fs rồi khóa candidate trước external test

### 04. YOLOv8s-seg hư hỏng đúng miền

- **Bằng chứng kỹ thuật:** Fine-tune CarDD; checkpoint hash-locked; adapter và overlay chạy live
- **KPI nghiệp vụ:** Useful-region rate; false regions/image; thời gian xem ảnh
- **Điều kiện đạt:** Validation ảnh bảo hiểm Việt Nam theo loại xe, góc chụp và lớp hư hỏng
- **Việc tiếp theo:** Gắn nhãn ảnh đúng miền; error gallery crack/dent/scratch; fine-tune candidate mới

### 05. DiT và LayoutLMv3 trên chứng từ bảo hiểm Việt Nam

- **Bằng chứng kỹ thuật:** DiT independent macro-F1 0.9283 trên RVL-CDIP; LayoutLMv3 final field F1 0.8659 trên SROIE; pipeline live đã nối.
- **KPI nghiệp vụ:** Routing accuracy; date/amount/plate/shop field accuracy; correction rate
- **Điều kiện đạt:** Taxonomy và validation riêng cho biên bản, báo giá, hóa đơn, đăng ký xe Việt Nam
- **Việc tiếp theo:** Chốt field schema nghiệp vụ và gắn nhãn validation mới; không tối ưu trên final test cũ

### 06. Consistency rules và NetworkX

- **Bằng chứng kỹ thuật:** Rule v2 và point-in-time graph v2 chạy local, có timestamp gate, entity hashing, chuẩn hóa biển số/điện thoại/xưởng và fallback khi field sai định dạng; validation hiện mới là synthetic engineering demo.
- **KPI nghiệp vụ:** Alert precision; số liên kết hữu ích; false investigation rate
- **Điều kiện đạt:** Rule owner phê duyệt tolerance; entity-resolution benchmark; mọi edge có available_at
- **Việc tiếp theo:** Tạo tập case đã xác minh, đo alert precision và xin rule-owner sign-off

### 07. Benchmark nguồn gốc và chỉnh sửa ảnh

- **Bằng chứng kỹ thuật:** Metadata, C2PA hook, exact/near reuse, editing trace và guided capture chạy local; manifest/evaluation scaffold đã có.
- **KPI nghiệp vụ:** Coverage; precision/recall theo nhóm; false accusation rate
- **Điều kiện đạt:** Benchmark camera/edit/social/screenshot/AI/reuse đúng miền, tách source-group
- **Việc tiếp theo:** Thu thập benchmark có provenance và khóa validation/test theo source image

### 08. Pixel forensic detector có calibration gate

- **Bằng chứng kỹ thuật:** Runtime chỉ nạp pixel model khi có đủ checkpoint và calibration manifest; mặc định tắt và trả inconclusive khi không đủ căn cứ.
- **KPI nghiệp vụ:** False accusation rate và calibration error dưới ngưỡng được duyệt
- **Điều kiện đạt:** Checkpoint hash, threshold chọn trên validation và frozen test đạt ngưỡng
- **Việc tiếp theo:** Huấn luyện/đánh giá sau khi milestone benchmark đủ dữ liệu

### 09. UI diễn giải technical value thành hành động nghiệp vụ

- **Bằng chứng kỹ thuật:** Dashboard, workbench, audit history và model proof dùng chung một ứng dụng; API client ổn định và cache bị vô hiệu hóa.
- **KPI nghiệp vụ:** Task completion; thời gian xử lý; tỷ lệ hiểu đúng; UAT pass rate
- **Điều kiện đạt:** UAT với giám định viên và bàn giao UI/backend được ký duyệt
- **Việc tiếp theo:** Chạy UAT theo golden cases, sửa wording và đo thời gian hoàn tất tác vụ
