# Vận hành dữ liệu chứng từ v1

**Ngày:** 10/10/2026  
**Mục tiêu:** gom dữ liệu nhiều nguồn vào một cấu trúc có thể kiểm tra, không sao chép lộn xộn và không làm mất provenance.

## Cấu trúc chuẩn trên Google Drive

```text
AI_Project_Insurance_Acc 2/
├── data/
│   ├── registry/documents/
│   │   ├── document_sources_registry.json
│   │   └── intake_runs/
│   ├── bronze/documents/
│   │   ├── cord_v2/v2/raw/
│   │   ├── funsd/original_2019/raw/
│   │   ├── xfund/v1.0/raw/
│   │   ├── sroie/ICDAR2019/raw/
│   │   ├── midv500/v1/raw/
│   │   ├── midv2020/v1/raw/
│   │   └── rvl_cdip/mirror_main/sample_raw/
│   ├── quarantine/documents/
│   ├── silver/documents/
│   │   ├── classification/
│   │   ├── ocr/
│   │   ├── layout/
│   │   └── kie/
│   └── gold/documents/
│       └── benchmarks/
├── artifacts/document/
└── reports/data_audit/documents/
```

Mỗi source/version chỉ có một thư mục Bronze chuẩn. Notebook và model đọc từ đó hoặc từ view tạm trong `/content`; không copy thêm một bản raw vào mỗi experiment.

## Ba lớp dữ liệu

- **Bronze:** file nguyên gốc, archive/snapshot, license, source manifest. Không sửa.
- **Silver:** schema chuẩn hóa, OCR text, page images, entities và quality flags. Có lineage về Bronze.
- **Gold:** split benchmark đã khóa cho một task cụ thể. Không dùng Gold của task này làm ground truth cho task khác.

## Quy tắc đặt tên

- Dataset: chữ thường và dấu gạch dưới, ví dụ `cord_v2`.
- Version: version/revision thật, ví dụ `v2`, `v1.0`, `original_2019`.
- Run: `<task>_<model>_<dataset>_<yyyymmdd>_<n>`.
- Không dùng tên `final`, `new`, `new2`, `copy` cho dữ liệu.

## Manifest tối thiểu

Mỗi dataset/version phải có `source_manifest.json` gồm:

- `dataset_name`, `version`, `source_url`, `acquisition_method`;
- `downloaded_at`, `revision` hoặc release tag;
- file list với size và checksum công bố/đã tính;
- license/terms URL và file license local;
- expected/observed counts, split và annotation schema;
- `status`: registered/downloaded/verified/quarantined/approved;
- ghi chú PII, restriction và redistribution.

## Cách tải

Notebook `Document_Data_Intake_Acc2_v1.ipynb` thực hiện:

1. Mount Drive và kiểm tra dung lượng.
2. Tạo registry/bronze/quarantine/report directories.
3. Tải tự động CORD v2, FUNSD và XFUND từ nguồn đã khóa.
4. Đăng ký SROIE từ file RRC hoặc Kaggle mirror do người dùng chỉ định.
5. Tải MIDV theo từng file Zenodo; không mặc định kéo 32,9 GB MIDV-500.
6. Với RVL-CDIP, mặc định dùng sample có kiểm soát; full archive 38,8 GB chỉ mở khi đủ dung lượng và scope classification đã duyệt.
7. Tạo inventory và manifest; không giải nén archive không tin cậy bằng đường dẫn traversal.

## Kaggle trên Colab

Ưu tiên Colab Secrets:

1. Kaggle → Settings → API → tạo token.
2. Colab → biểu tượng chìa khóa **Secrets**.
3. Tạo `KAGGLE_API_TOKEN`, bật quyền notebook đọc secret.
4. Không dán token vào cell, output, Git hoặc Google Drive.
5. Trong notebook, gọi `kagglehub.login()` chỉ khi secret chưa được cấu hình.

Mirror phải được ghi bằng handle có owner và version, ví dụ `owner/dataset/versions/3`; không dùng “latest” mà không ghi lại version.

## Hugging Face trên Colab

- Public dataset không cần token.
- Dùng `snapshot_download(..., revision=<commit>)` để pin dữ liệu nhỏ/vừa.
- Với dataset lớn, dùng streaming hoặc tải theo file; không tạo cả cache trong `/root/.cache` rồi lại copy sang Drive.
- Nếu cần token cho gated dataset, đặt `HF_TOKEN` trong Colab Secrets; không ghi token vào notebook.

## Gate dung lượng

Ước lượng raw hiện tại:

| Nguồn | Dung lượng gần đúng |
|---|---:|
| CORD v2 | 2,31 GB |
| FUNSD | dưới 0,1 GB |
| XFUND | kiểm tra release trước khi tải |
| MIDV-500 | 32,9 GB |
| MIDV-2020 Zenodo | 17,4 GB |
| RVL-CDIP | 38,8 GB |

Không nên tải toàn bộ MIDV-500, MIDV-2020 và RVL-CDIP trong cùng một Colab/Drive nhỏ. Tải theo task và giữ tối thiểu 20% dung lượng trống để staging, giải nén và cache.

## Thứ tự thực hiện

1. CORD v2 + FUNSD + XFUND để dựng baseline OCR/KIE/form understanding.
2. SROIE sau khi khóa nguồn RRC hoặc mirror/version.
3. Chỉ mở MIDV khi scope có giấy tờ định danh.
4. RVL-CDIP bắt đầu bằng sample cân bằng; audit PII/duplicate trước training.

Nếu SROIE chưa có archive RRC hoặc Kaggle handle, notebook dùng mirror hiệu chỉnh `jsdnrs/ICDAR2019-SROIE` tại commit đã ghim. Manifest phân biệt rõ nguồn gốc RRC và mirror, đồng thời giữ trạng thái `pending_audit` cho tới khi kiểm tra số mẫu, schema, license và checksum hoàn tất.

### RVL-CDIP loader compatibility

Dataset script upstream hiện còn các URL lịch sử dạng `datasets/rvl_cdip` không có namespace. `huggingface_hub` mới có thể báo `HfUriError`. Notebook tạo một bản compatibility loader cục bộ, thay đúng bốn URL bằng namespace `datasets/aharley/rvl_cdip`, kiểm tra số lượng thay thế và ghi SHA-256 của loader vào manifest. Chỉ cần chạy lại notebook từ đầu; các nguồn đã có sẽ được reuse và cell RVL sẽ lấy lại sample.
5. Sau inventory, chốt một baseline nhỏ. Không train đồng thời trên tất cả nguồn.

## Liên kết với claim

Dữ liệu public không có `claim_id`. Chỉ đầu ra của module chứng từ trên tài liệu nghiệp vụ thật mới nối vào claim theo `DOCUMENT_CLAIM_INTEGRATION_CONTRACT_V1.md`. Không ghép dataset public với bảng fraud hoặc CarDD theo tên file hay thứ tự dòng.
