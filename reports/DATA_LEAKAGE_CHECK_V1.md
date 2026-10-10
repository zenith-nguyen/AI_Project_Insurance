# Data Leakage Check v1

## Các kiểm tra đã thực hiện

- Exact image SHA-256 overlap giữa train/validation/test.
- Số mẫu và schema theo split.
- Ảnh hỏng/không decode được.
- File thiếu, orphan label và invalid annotation đối với CarDD.
- Checksum/ZIP safety đối với XFUND.
- Cân bằng 16 lớp đối với RVL-CDIP sample.

## Kết quả

| Dataset | Kết quả leakage |
|---|---|
| CarDD | Không thiếu label, không orphan label, split đã khóa trước training |
| CORD v2 | 0 exact duplicate chéo train/validation/test |
| SROIE raw mirror | 8 exact duplicate train/test; raw split không sạch |
| FUNSD | Hai storage tree của cùng bộ 199 mẫu; audit chọn một canonical root |
| XFUND | 0 exact duplicate train/validation |
| RVL-CDIP sample | Sample 1.600 ảnh được kiểm tra hash/decode/balance; chưa dùng test để chọn model |

## Remediation SROIE

- Test 361 mẫu được giữ nguyên.
- Tám row trùng test bị loại khỏi source train 626 mẫu.
- Clean train pool còn 618 row.
- Các exact duplicate nội bộ được gom theo image SHA-256.
- Group-aware deterministic split tạo 525 train và 93 validation.
- Artifact chỉ được ghi khi train/validation, train/test và validation/test đều có overlap bằng 0.

## Kiểm tra còn cần làm

- Near duplicate bằng perceptual hash/embedding trước final document benchmark.
- Trùng nội dung sau OCR dù ảnh khác crop/resize.
- Trùng template/vendor/date giữa split đối với dữ liệu nghiệp vụ thật.
- Leakage theo `claim_id`, customer, vehicle và incident; mọi tài liệu của cùng claim phải ở cùng split.
