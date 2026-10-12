# DiT Independent Validation v1

**Ngày chạy:** 12/10/2026  
**Notebook:** `Document_DiT_Independent_Validation_Acc2_v2.ipynb`  
**Model:** `microsoft/dit-base-finetuned-rvlcdip`  
**Model revision:** `23f8b03d130fb66bbc9a15df3c75d753e49240eb`

## Protocol

- Nguồn validation: `chainyo/rvl-cdip`, revision `66f430a1252ea1732413a80a56a1b6e8bc74264e`.
- Split: `val`.
- Sample cân bằng: 320 ảnh, 20 ảnh cho mỗi lớp trong 16 lớp.
- Mỗi ảnh cache trên Drive có SHA-256 và manifest.
- Sample upstream `train` dùng trong smoke baseline không được tái sử dụng.
- Test split không được đọc.

## Kết quả

| Metric | Smoke sample từ upstream train | Independent validation |
|---|---:|---:|
| Macro-F1 | 0,962618 | **0,928260** |
| Balanced accuracy | 0,962500 | **0,928125** |

Macro-F1 giảm `0,034358` so với smoke metric. Independent validation là bằng chứng phù hợp hơn để báo cáo vì không đánh giá lại trên sample lấy từ split đã dùng để fine-tune model.

## Giới hạn

Kết quả vẫn thuộc RVL-CDIP và chỉ gồm 320 ảnh. Nó chưa chứng minh khả năng phân loại repair estimate, biên bản cảnh sát, giấy tờ tùy thân hoặc chứng từ bảo hiểm Việt Nam. RVL-CDIP còn có rủi ro label noise, overlap và domain cũ; trước MVP cần một validation set nghiệp vụ có consent.

**Manifest trên Drive:**

`/content/drive/MyDrive/AI_Project_Insurance_Acc 2/data/bronze/documents/rvl_cdip/mirror_main/independent_validation_sample_v1/sample_manifest.jsonl`

**Report gốc trên Drive:**

`/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/documents/dit_rvl_official_validation_v1.json`
