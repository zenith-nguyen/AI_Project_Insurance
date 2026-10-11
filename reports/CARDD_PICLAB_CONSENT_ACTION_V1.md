# CarDD PIC Lab Consent — Action and Evidence Plan v1

## Trạng thái

`OPEN`: repo chưa có bằng chứng PIC Lab đã cho phép nhóm sử dụng CarDD cho nghiên cứu này. Không được ghi là đã xin phép khi chưa có thư/email xác nhận.

## Việc cần làm

1. Một thành viên liên hệ PIC Lab/chủ dataset bằng kênh chính thức.
2. Nêu tên trường/môn học, mục đích nghiên cứu, phạm vi dùng CarDD và việc không phân phối raw data.
3. Hỏi rõ quyền train model, trình bày metric, lưu checkpoint nội bộ và chia sẻ demo.
4. Lưu phản hồi gốc dạng PDF/EML hoặc ảnh chụp đầy đủ header.
5. Tính SHA-256 file bằng chứng và ghi người nhận, ngày, phạm vi consent.
6. Không đưa địa chỉ email cá nhân hoặc nội dung nhạy cảm vào Git public; chỉ lưu evidence trong Drive hạn chế quyền.

## Vị trí bằng chứng đề xuất trên Drive

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/governance/licenses/cardd/
├── LICENSE_SOURCE.pdf
├── PICLAB_CONSENT_RESPONSE.pdf
└── consent_manifest.json
```

## Trường tối thiểu của consent manifest

```json
{
  "dataset": "CarDD",
  "status": "pending",
  "requested_at": null,
  "received_at": null,
  "scope": null,
  "evidence_path": null,
  "evidence_sha256": null,
  "restrictions": [
    "no_raw_redistribution",
    "research_only_until_confirmed"
  ]
}
```

## Cách trình bày hiện tại

“Nhóm đã đọc điều kiện sử dụng và xác định prior consent là một governance gate. Bằng chứng consent hiện chưa có, nên nhóm giữ trạng thái OPEN, không phân phối raw CarDD và không tuyên bố quyền sử dụng thương mại.”
