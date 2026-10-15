# Kiểm toán và kế hoạch sử dụng bộ 27 hồ sơ demo

Ngày kiểm toán: 2026-10-16
Kết luận: **PASS có điều kiện cho engineering demo/UAT; không phải validation dữ liệu bảo hiểm thật**

## Bộ dữ liệu chứa gì?

- 27 hồ sơ tổng hợp, chia thành 9 kịch bản; mỗi kịch bản có 3 biến thể.
- 6 ảnh xe nền do công cụ tạo ảnh sinh ra.
- 54 PDF một trang gồm tờ khai và báo giá.
- 9 ảnh giấy đăng ký/bảo hiểm/đăng kiểm dùng chung theo 3 xe mô phỏng.
- Expected outcome riêng cho 27 case, gồm hướng xử lý, tín hiệu mong đợi và giới hạn.
- Fixture riêng cho metadata, OCR, ảnh tái sử dụng và graph ở các case cần thiết.

Ký hiệu `P/N/H/C` là vai trò trong kịch bản, không phải nhãn gian lận. Tất cả expected file đều ghi `fraud_outcome=unknown` và `human_review_required=true`.

## Kết quả kiểm toán nguồn

| Kiểm tra | Kết quả |
|---|---:|
| Case trong run manifest | 27/27 |
| Scenario | 9, mỗi scenario 3 case |
| Mục trong asset manifest | 224 |
| File thiếu so với manifest | 0 |
| File sai SHA-256 | 0 |
| PDF đọc được | 54/54 |
| PDF có text layer | 54/54 |
| PNG trong input chính | 42 |
| PNG lỗi | 2 |
| Claim có đường dẫn chứng từ lặp | 14 |
| Case graph có oracle nhìn tham chiếu tương lai | 3 |

Hai PNG báo giá lỗi là file rỗng của `CLM-03-P` và file PNG bị cắt của `CLM-07-N`. PDF nguồn tương ứng vẫn hợp lệ và có text. Bản chuẩn hóa render lại **toàn bộ 27 ảnh báo giá từ PDF** để cùng một quy trình, thay vì chỉ vá hai file lỗi. Đường dẫn chứng từ lặp được loại nhưng bản nguồn không bị sửa.

Ba case SC07 đặt hai hồ sơ tham chiếu sau thời điểm hồ sơ mục tiêu, trong khi expected result giả định các liên kết đó đã tồn tại. Đây là xung đột với kiểm soát point-in-time: hệ thống thật không được nhìn dữ liệu tương lai. Importer UAT vì thế phản chiếu khoảng cách thời gian của reference về trước target, đồng thời ghi `original_scored_at`, `imported_scored_at` và cờ `timestamp_rebased_for_point_in_time_uat` trong receipt. Biến đổi này chỉ dùng cho synthetic UAT và không sửa dữ liệu nguồn.

## Bản chuẩn hóa

Bản dùng cho hệ thống nằm ngoài Git tại:

```text
D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1
```

Bản này có:

- `suite_manifest.json`: danh mục 27 case và đường dẫn đã chuẩn hóa;
- `cases/`: claim, PDF và fixture theo case;
- `assets/`: ảnh xe và giấy tờ dùng chung;
- `expected_private/`: đáp án được tách khỏi input model;
- `ocr_benchmark/`: 27 ảnh báo giá render lại và transcript từ text layer;
- `source_audit.json`: kết quả kiểm toán nguồn;
- `integrity_manifest.json`: SHA-256 của 222 file đầu ra.

Expected outcome không được đưa vào prompt, feature hay input model. Nó chỉ được đọc sau inference để chấm UAT.

## Tận dụng theo từng kịch bản

| Scenario | Dùng để kiểm tra | Trạng thái sử dụng |
|---|---|---|
| SC00 | Hồ sơ đủ/thiếu ảnh và chi phí cao hợp lệ | Intake, evidence completeness và fallback |
| SC01 | Ảnh hư hỏng so với hạng mục báo giá | UAT consistency; cần taxonomy bộ phận tốt hơn |
| SC02 | Ảnh trùng, ảnh khác và cùng xe khác góc | Exact/near reuse với history tách riêng |
| SC03 | Biển số khai báo so với chứng từ/ảnh | OCR/KIE và rule đối chiếu |
| SC04 | Ảnh mô phỏng chụp lại màn hình | Engineering demo; không đo accuracy thật |
| SC05 | Thời gian ảnh so với sự cố | Rule test trên fixture EXIF; không phải EXIF thật |
| SC06 | Tổng tiền yêu cầu so với báo giá | OCR/KIE và amount consistency |
| SC07 | Nhiều hồ sơ dùng chung xe/liên hệ/xưởng | NetworkX point-in-time và false-positive guard |
| SC08 | Ảnh nguồn, ảnh chỉnh tăng hư hỏng và ảnh mờ | Authenticity research; chưa phải codec benchmark |

## OCR benchmark 27 trang

27 ảnh báo giá được xếp vào tier `synthetic_engineering`. Transcript lấy từ text layer của PDF sinh tài liệu và được đánh dấu `source_verified`.

Tier này dùng được để:

- phát hiện candidate OCR nào tệ hơn baseline;
- đo latency và lỗi dấu/chữ/số trên bố cục tổng hợp;
- kiểm tra runner resume và báo cáo lỗi theo trang.

Tier này **không được** dùng để nói PaddleOCR đã chính xác trên chứng từ bảo hiểm Việt Nam thật. Report luôn khóa `enough_pages_for_domain_claim=false`, kể cả khi engineering gate PASS.

## Công cụ đã bổ sung

Chuẩn hóa lại bộ dữ liệu:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_demo27_suite.py `
  --source "D:\My Dowload\Bộ 27 hồ sơ demo" `
  --output "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1" `
  --overwrite
```

Nạp một case quan hệ vào ứng dụng:

```powershell
.\.venv\Scripts\python.exe scripts\import_demo27_case.py `
  --pack "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1" `
  --case CLM-07-P `
  --seed-history `
  --documents minimal `
  --analyze
```

`minimal` tải ảnh xe và một ảnh báo giá để demo nhanh. `full` tải toàn bộ nhóm chứng từ đã khử trùng. History của SC02/SC07 chỉ được seed trong phạm vi case tương ứng để tránh 27 case dùng chung ảnh tạo cảnh báo giả.

`none` không tải chứng từ và chỉ dành cho test cô lập graph/ảnh; nó phải hiện thiếu chứng từ và không được dùng để chứng minh luồng end-to-end.

Riêng SC07, timestamp reference tương lai trong nguồn được dịch về quá khứ cho point-in-time UAT; receipt lưu đầy đủ thời gian gốc và thời gian import.

Mỗi lần import có `relationship_scope` riêng. Graph chỉ so sánh claim trong cùng scope, tránh các lần demo trước hoặc các nhóm dữ liệu khác làm tăng liên kết giả; scope không được tính như một thực thể rủi ro.

Kiểm tra lại toàn bộ 222 hash và đường dẫn trước khi demo:

```powershell
.\.venv\Scripts\python.exe scripts\validate_demo27_suite.py `
  --pack "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1"
```

Tạo ma trận actual/expected sau mỗi đợt chạy:

```powershell
.\.venv\Scripts\python.exe scripts\summarize_demo27_runs.py `
  --pack "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1" `
  --output "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1\run_matrix.json"
```

Ma trận không tự tuyên bố PASS nghiệp vụ. Nó để expected route cạnh output thực tế và giữ `human_signoff=pending` cho đến khi người phụ trách nghiệp vụ duyệt.

## Kết luận sử dụng

Bộ 27 hồ sơ nâng golden rehearsal từ vài ví dụ rời rạc thành một ma trận UAT có positive, negative và hard-negative. Nó có giá trị để kiểm tra luồng, diễn giải, rule, graph, cache và failure handling. Nó chưa làm thay đổi trạng thái `waiting_for_domain_data` của OCR/YOLO/authenticity vì toàn bộ ảnh là tổng hợp, không có mask hư hỏng, bounding box OCR hoặc ground truth claim thật.

## Kết quả chạy thực tế ngày 2026-10-16

- OCR đã chạy đủ 27/27 báo giá cho hai candidate; `fast640` bị promotion gate loại vì nhanh hơn nhưng CER kém hơn.
- SC07-P graph-only smoke đã import hai lịch sử với timestamp rebased, chạy trong scope riêng và tìm đúng 2/2 claim tham chiếu, không lẫn các lần demo cũ.
- Smoke trả `priority=high` theo tín hiệu quan hệ và `analysis_status=blocked` vì cố ý không tải chứng từ. Đây là fallback đúng của test cô lập, không phải lỗi graph.
- Ma trận UAT hiện có 1/27 case đã chạy actual, 26/27 chưa chạy end-to-end và vẫn chờ human sign-off. Không tuyên bố bộ 27 đã PASS nghiệp vụ.
