# Kết quả SROIE Processed Split v1

**Ngày chạy:** 11/10/2026

**Nguồn bằng chứng:** output Colab do nhóm cung cấp
**Report trên Drive:** `/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/data_audit/documents/sroie_processed_split_v1.json`

## Kết quả

| Kiểm tra | Kết quả |
|---|---:|
| Raw train | 626 |
| Raw test | 361 |
| Duplicate raw train trùng test đã loại | 8 |
| Processed train | 525 |
| Processed validation | 93 |
| Processed test | 361 |
| Unique image groups trong clean pool | 613 |
| Internal duplicate groups được giữ cùng split | 5 |
| Train–validation exact overlap | 0 |
| Train–test exact overlap | 0 |
| Validation–test exact overlap | 0 |
| Test dùng để chọn model | Không |

**Data gate:** PASS. Processed split có thể dùng cho baseline và model selection. Test vẫn khóa.
