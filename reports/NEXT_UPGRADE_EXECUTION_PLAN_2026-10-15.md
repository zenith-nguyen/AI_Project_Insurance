# Kế hoạch nâng cấp tiếp theo — Claim Review Workbench

Ngày khóa kế hoạch: 2026-10-15  
Mục tiêu gần nhất: `research_handoff`  
Mục tiêu sau đó: `controlled_pilot`

## Nguyên tắc quyết định

Mỗi hạng mục phải có đồng thời:

- **technical value:** metric, latency, split và artifact có thể kiểm tra lại;
- **business value:** giúp người duyệt xem nhanh hơn, giảm nhập lại, tìm đúng hồ sơ cần chú ý hoặc yêu cầu đúng bằng chứng còn thiếu;
- **fallback:** thiếu model hoặc thiếu dữ liệu vẫn trả kết quả phần đã chạy và nói rõ phần chưa kiểm tra;
- **human decision:** hệ thống không tự kết luận gian lận hoặc tự từ chối bồi thường.

## Mốc A — Đo đúng trước khi tối ưu

### Công việc

1. Ghi tổng thời gian phân tích và thời gian của từng công đoạn: XGBoost, nguồn gốc ảnh, YOLO, DiT, PaddleOCR, LayoutLMv3, graph và tổng hợp.
2. Hiển thị công đoạn hiện tại, thời gian đã chạy và công đoạn chậm nhất trên màn hình nạp hồ sơ.
3. Lưu báo cáo benchmark theo cold run, warm run và cache hit.

### Giá trị nghiệp vụ

Người demo biết hệ thống vẫn đang chạy ở bước nào. Đội phát triển biết chính xác module nào cần tối ưu, tránh sửa theo cảm giác.

### Definition of Done

- Job API trả `stage_durations_seconds` và `current_stage_elapsed_seconds`.
- UI cập nhật tối thiểu mỗi giây và nêu công đoạn chậm nhất khi hoàn tất.
- Cache hit không chạy lại model nếu hồ sơ và bằng chứng không đổi.
- Có số đo cho ba hồ sơ demo v2 trên cùng một cấu hình máy.

Trạng thái: **hoàn thành**. Benchmark Hybrid KIE v2 đạt 3/3 business gate; cache hit đạt 0,0 giây. PaddleOCR chiếm 328,3/389,2 giây và là nút thắt cần xử lý tiếp.

## Mốc B — Golden rehearsal và UAT nghiên cứu

### Công việc

1. Chạy ba hồ sơ demo v2 theo thứ tự 01 → 02 → 03.
2. Với mỗi case, đối chiếu output với expected business outcome:
   - case 01: đủ ảnh/chứng từ, mở được bằng chứng, lưu review;
   - case 02: tìm được quan hệ dùng chung điện thoại/xưởng nhưng không kết luận gian lận;
   - case 03: phát hiện metadata khai báo AI/chỉnh sửa và yêu cầu rà soát.
3. Kiểm tra audit replay: quyết định và correction vẫn đọc lại được sau khi tải lại trang.
4. Ghi task completion, lỗi hiểu sai, thời gian hoàn thành và góp ý wording.

### Definition of Done

- 3/3 case không lỗi im lặng.
- Mọi tín hiệu liên kết được tới evidence và model/rule version.
- 3/3 review được lưu và đọc lại.
- Một thành viên không viết backend chạy được theo hướng dẫn.
- Có biên bản UAT nghiên cứu và chữ ký/người xác nhận.

Lưu ý: PASS mốc này chứng minh luồng sản phẩm; chưa chứng minh độ chính xác trên claim bảo hiểm Việt Nam thật.

## Mốc C — Giảm thời gian phản hồi

Trạng thái 2026-10-16: **đã hoàn thành preload và cache theo từng evidence**. Kịch bản thêm một ảnh giảm từ lần chạy đầy đủ 145,6 giây xuống 2,5 giây; ảnh và chứng từ cũ không chạy lại. Phần còn lại của mốc là tối ưu thời gian OCR cho evidence mới trên validation đúng miền.

Chỉ thực hiện sau khi có benchmark Mốc A.

### Hướng tối ưu theo thứ tự

1. Nạp model một lần khi server khởi động và tái sử dụng processor/session.
2. Chuẩn hóa kích thước ảnh đầu vào; từ chối hoặc resize tệp quá lớn theo policy có audit.
3. Không chạy lại authenticity, OCR hoặc YOLO khi SHA-256 của evidence và model version không đổi.
4. Tách phân tích ảnh và chứng từ thành task độc lập nếu cấu hình CPU/GPU cho phép.
5. Lưu job và stage timing bền vững để không mất lịch sử sau khi restart.

### Gate nghiên cứu đề xuất

- UI phản hồi việc đã nhận hồ sơ trong dưới 2 giây.
- Cache hit dưới 5 giây.
- Warm full run p50 mục tiêu dưới 90 giây trên máy demo hiện tại.
- Không giảm metric và không bỏ qua module để đạt latency.

## Mốc D — Chất lượng chứng từ Việt Nam

Trạng thái 2026-10-16: **đã hoàn thành protocol, manifest validation, metric runner và candidate runner có resume**. Chưa có 50–100 trang được adjudicate nên chưa có metric độ chính xác đúng miền và chưa được chọn cấu hình OCR mới.

### Dữ liệu cần có

Tối thiểu 50–100 trang đã được phép sử dụng, bao phủ biên bản hiện trường, báo giá, hóa đơn, đăng ký xe; có ground truth cho loại tài liệu, ngày, tổng tiền, biển số và xưởng.

### Thử nghiệm

- orientation detection và auto-rotate;
- deskew, crop, contrast và denoise;
- cấu hình PaddleOCR tiếng Việt;
- crop theo vùng trước OCR;
- LayoutLMv3 chỉ tối ưu trên train/validation mới, không đọc lại final test đã khóa.

### KPI

- exact/normalized field accuracy cho ngày, tổng tiền, biển số và xưởng;
- correction rate;
- thời gian người duyệt đọc một chứng từ;
- tỷ lệ confidence thấp được chuyển đúng sang con người.

## Mốc E — XGBoost và hàng đợi nghiệp vụ

1. Liên kết feature S1–S5 theo `claim_id` và `available_at` trên `train_fs/val_fs`.
2. So sánh XGBoost với Logistic Regression và rules bằng AP, Recall@K, precision trong queue và calibration.
3. Chốt chi phí review, false hold và missed investigation để tính Net Value.
4. Khóa candidate trước khi dùng external/frozen test mới.

Business gate: cùng năng lực duyệt K%, model tìm thêm case cần điều tra và Net Value không giảm. Điểm vẫn là điểm xếp hạng, không phải xác suất gian lận.

## Mốc F — YOLO đúng miền

1. Thu thập ảnh được phép dùng theo loại xe, góc chụp, ánh sáng và loại hư hỏng.
2. Hai người kiểm tra mask cho `crack`, `dent`, `scratch` và các lớp nghiệp vụ mới.
3. Lập error gallery và fine-tune candidate trên train/validation mới.
4. Đo `useful-region rate`, false regions/image và thời gian xem ảnh cùng mAP.

Business gate: vùng khoanh giúp giám định viên tìm đúng chỗ cần xem nhanh hơn; vùng yếu luôn yêu cầu xác nhận.

## Mốc G — Graph, rules và nguồn gốc ảnh

### Graph/rules

- benchmark normalization biển số, điện thoại và xưởng;
- mọi edge có `available_at`;
- đo alert precision và false investigation rate;
- tolerance được rule owner phê duyệt.

### Media authenticity

- benchmark camera gốc, chỉnh sửa hợp lệ, Photoshop/AI edit, social re-encode, screenshot/re-capture, nhiều generator và near-duplicate;
- tách train/validation/test theo ảnh nguồn để tránh leakage;
- đo coverage, precision/recall theo nhóm và false accusation rate;
- pixel detector chỉ được bật khi checkpoint, threshold, calibration và test manifest đều PASS.

Không tìm thấy marker phải trả `inconclusive`; không được diễn giải thành “ảnh thật”.

## Mốc H — Pilot có kiểm soát

Chỉ bắt đầu sau `research_handoff` và khi có:

- dataset license/consent và quy trình PII;
- authentication, RBAC, encryption và retention;
- database/audit backup;
- load/security test;
- business UAT;
- monitoring, cảnh báo, rollback và owner trực vận hành.

## Thứ tự thực hiện ngay

| Thứ tự | Việc | Có thể làm ngay? | Đầu ra |
|---:|---|---|---|
| 1 | Stage timing và bottleneck UI | Có | API/UI đã bổ sung |
| 2 | Benchmark ba case demo v2 | Có | Báo cáo cold/warm/cache |
| 3 | Golden rehearsal + UAT | Có | Biên bản PASS/FAIL và góp ý |
| 4 | Cache/model warm-up theo bottleneck | Có sau benchmark | Candidate tối ưu latency |
| 5 | OCR benchmark infrastructure | Đã hoàn thành | Protocol, validation gate, runner có resume |
| 6 | OCR/YOLO/domain validation | Cần dữ liệu được phép dùng | Báo cáo metric đúng miền |
| 7 | XGBoost S1–S5 + Net Value | Cần feature và cost matrix | Candidate xếp hạng mới |
| 8 | Security/load/UAT pilot | Sau research handoff | Pilot readiness report |

## Trạng thái “done” cần nói khi báo cáo

- **Hiện tại:** engineering prototype/research system đã chạy end-to-end và có safeguard.
- **Research handoff hoàn thành khi:** multimodal live, golden run, handbook và bàn giao UI/backend được ký xác nhận.
- **Pilot-ready hoàn thành khi:** validation đúng miền, security/load/UAT và vận hành đều PASS.
- **Chưa được tuyên bố:** hệ thống tự động phát hiện mọi ảnh AI, tự kết luận gian lận hoặc sẵn sàng production.
