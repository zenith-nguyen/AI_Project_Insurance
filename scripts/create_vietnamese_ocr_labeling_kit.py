"""Create a private, empty labeling workspace for Vietnamese insurance documents."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty folder: {root}")
    for folder in ("images", "transcripts", "adjudication", "reports"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    example = {
        "sample_id": "VN-OCR-0001",
        "split": "validation",
        "image_path": "images/VN-OCR-0001.png",
        "image_sha256": "<sha256-after-redaction>",
        "document_type": "repair_estimate",
        "reference_text_path": "transcripts/VN-OCR-0001.txt",
        "reference_fields": {
            "total_vnd": "<verified-digits>",
            "document_date": "<dd/mm/yyyy>",
            "plate_number": "<verified-plate>",
        },
        "annotation_status": "adjudicated",
        "consent_or_legal_basis": "<approval-code>",
        "pii_treatment": "redacted",
        "benchmark_tier": "domain_validation",
    }
    (root / "manifest.example.json").write_text(
        json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "manifest.jsonl").touch()
    with (root / "adjudication" / "field_labels.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerow([
            "sample_id", "annotator_1", "annotator_2", "adjudicator", "document_type",
            "document_date", "total_vnd", "plate_number", "status", "notes",
        ])
    with (root / "consent_log.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerow([
            "approval_code", "data_owner_role", "allowed_purpose", "retention_until", "approved_by", "status",
        ])
    (root / "00_README.md").write_text(
        "# Bộ gán nhãn OCR chứng từ Việt Nam (private)\n\n"
        "1. Chỉ nhận trang có quyền sử dụng và ghi mã phê duyệt vào `consent_log.csv`.\n"
        "2. Che tên, số điện thoại, địa chỉ, chữ ký, số giấy tờ và dữ liệu cá nhân không cần cho metric.\n"
        "3. Mỗi trang dùng một `sample_id`; ảnh vào `images/`, transcript đúng vào `transcripts/`.\n"
        "4. Hai người gán nhãn độc lập; người thứ ba adjudicate ngày, tổng tiền, biển số và toàn văn.\n"
        "5. Chỉ thêm dòng vào `manifest.jsonl` khi `annotation_status=adjudicated`.\n"
        "6. Giữ thư mục này ngoài Git; chỉ commit báo cáo aggregate không chứa text/PII.\n\n"
        "Mục tiêu tối thiểu: 50 trang; khuyến nghị 100 trang, phủ biên bản hiện trường, báo giá, hóa đơn, "
        "đăng ký xe và chứng nhận bảo hiểm. Không để cùng một hồ sơ xuất hiện ở nhiều split.\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(root), "status": "ready_for_private_labeling"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
