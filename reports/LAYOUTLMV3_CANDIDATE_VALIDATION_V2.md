# LayoutLMv3 KIE Candidate Validation v2

**Ngày chạy:** 12/10/2026  
**Notebook:** `Document_LayoutLMv3_Candidate_Acc2_v3.ipynb`  
**Dữ liệu:** SROIE processed v1 — 525 train, 93 validation, 361 test khóa  
**Phạm vi field:** `date`, `total`

## Kết quả data gate

| Kiểm tra | Kết quả |
|---|---:|
| Date expected / matched | 93 / 93 |
| Total expected / matched | 93 / 91 |
| Weak-alignment coverage | **0,989247** |
| Ngưỡng coverage đã khóa | 0,85 |
| Test được đọc | **Không** |

Hai total không align được là các trường hợp OCR nguồn làm vỡ hoặc mất chữ số. Notebook ghi lại đầy đủ target và OCR words để audit; không tự bịa nhãn thay thế.

## So sánh model

| Model | Precision | Recall | Field micro-F1 |
|---|---:|---:|---:|
| Isolated rule KIE baseline | 0,819549 | 0,586022 | 0,683386 |
| LayoutLMv3 best checkpoint | **0,928962** | **0,913978** | **0,921409** |
| Chênh lệch candidate − baseline | +0,109413 | +0,327957 | **+0,238024** |

Quy tắc đặt trước yêu cầu candidate tăng ít nhất **0,02** field micro-F1 và alignment coverage đạt ít nhất **0,85**. Candidate đạt cả hai điều kiện, do đó `Candidate selected by locked rule: True`.

## Chọn checkpoint

Best checkpoint đến từ epoch 4:

- validation loss: `0,029946`
- BIO span precision: `0,907104`
- BIO span recall: `0,902174`
- BIO span F1: `0,904632`
- field precision: `0,928962`
- field recall: `0,913978`
- field micro-F1: `0,921409`

Epoch 5 đạt field micro-F1 `0,919786`, thấp hơn epoch 4. Trainer kết thúc đủ 5 epoch rồi nạp lại best checkpoint, vì vậy bảng evaluate cuối mang metric epoch 4 dù trạng thái training đã ở epoch 5.

## Quyết định và giới hạn

LayoutLMv3 được chọn làm KIE candidate cho hai trường ngày và tổng tiền trên validation SROIE. SROIE test 361 ảnh vẫn khóa; chưa được phép dùng test để tinh chỉnh hoặc tuyên bố final-test performance.

Kết quả này chưa chứng minh chất lượng trên chứng từ bảo hiểm Việt Nam, repair estimate, giấy tờ tùy thân hoặc các field ngoài `date`/`total`. Trước khi productization cần đánh giá theo field trên dữ liệu nghiệp vụ có consent, kiểm tra calibration/abstention và đo latency của pipeline OCR + KIE.

**Report gốc trên Drive:**

`/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/documents/layoutlmv3_sroie_candidate_validation_v2.json`

**Artifact trên Drive:**

`/content/drive/MyDrive/AI_Project_Insurance_Acc 2/artifacts/document/layoutlmv3_sroie_candidate_v2/`
