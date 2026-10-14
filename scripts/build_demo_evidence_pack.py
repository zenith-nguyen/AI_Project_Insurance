"""Build a local, synthetic demo pack for authenticity and relationship checks."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, PngImagePlugin


def copy_with_png_metadata(source: Path, target: Path, description: str) -> None:
    with Image.open(source) as image:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("description", description)
        image.convert("RGB").save(target, format="PNG", pnginfo=metadata)


def write_case(folder: Path, values: dict, expected: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "THONG_TIN_NHAP.json").write_text(
        json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "KET_QUA_MONG_DOI.txt").write_text(
        "\n".join(f"- {item}" for item in expected) + "\n", encoding="utf-8-sig"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--original-image", required=True, type=Path)
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--ai-unmarked", required=True, type=Path)
    parser.add_argument("--ai-edited", required=True, type=Path)
    args = parser.parse_args()

    output = args.output
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    case_a = output / "01_CLAIM_GOC"
    write_case(case_a, {
        "claim_amount": 67140, "incident_date": "2015-02-28", "plate_number": "51A-111.11",
        "contact_phone": "0909000111", "repair_shop": "GARAGE-DEMO-01",
    }, [
        "Ảnh chưa đủ bằng chứng để kết luận thật/AI nếu không có marker.",
        "YOLO khoanh vùng hư hỏng nếu checkpoint đang active.",
        "Chứng từ được OCR; KIE có thể không trích trường vì đây là biên bản tiếng Việt ngoài miền SROIE.",
        "Chưa có hồ sơ trước đó dùng chung thực thể.",
    ])
    shutil.copy2(args.original_image, case_a / "01_anh_xe_goc.png")
    shutil.copy2(args.document, case_a / "02_bien_ban_hien_truong.png")

    case_b = output / "02_CLAIM_ANH_TRUNG"
    write_case(case_b, {
        "claim_amount": 52000000, "incident_date": "2015-03-01", "plate_number": "51A-222.22",
        "contact_phone": "0909000111", "repair_shop": "GARAGE-DEMO-01",
    }, [
        "Nguồn gốc ảnh báo ảnh đã xuất hiện ở claim 01 và là bản trùng byte.",
        "Quan hệ báo hai thực thể dùng chung: số điện thoại và xưởng sửa chữa.",
        "Hệ thống đề nghị mở hồ sơ liên quan; đây chưa phải kết luận gian lận.",
    ])
    shutil.copy2(args.original_image, case_b / "01_anh_xe_tai_su_dung_y_nguyen.png")

    case_c = output / "03_CLAIM_ANH_NEN_RESIZE"
    write_case(case_c, {
        "claim_amount": 48000000, "incident_date": "2015-03-02", "plate_number": "51A-333.33",
        "contact_phone": "0909000333", "repair_shop": "GARAGE-DEMO-01",
    }, [
        "Ảnh được nhận là near_duplicate của claim 01/02 dù đã resize và nén JPEG.",
        "Quan hệ báo dùng chung xưởng sửa chữa.",
    ])
    with Image.open(args.original_image) as image:
        resized = image.convert("RGB").resize((384, 384), Image.Resampling.LANCZOS)
        resized.save(case_c / "01_anh_qua_mang_xa_hoi_gia_lap.jpg", format="JPEG", quality=48, optimize=True)

    case_d = output / "04_CLAIM_AI_KHONG_MARKER"
    write_case(case_d, {
        "claim_amount": 73000000, "incident_date": "2015-03-03", "plate_number": "51A-444.44",
        "contact_phone": "0909000444", "repair_shop": "GARAGE-AI-DEMO",
    }, [
        "Kết quả phải là chưa đủ bằng chứng xác định ảnh AI nếu file không có marker/C2PA.",
        "Case này chứng minh giới hạn: hệ thống không được phép đoán ảnh thật chỉ vì không thấy watermark.",
    ])
    shutil.copy2(args.ai_unmarked, case_d / "01_anh_ai_khong_marker.png")

    case_e = output / "05_CLAIM_AI_CO_KHAI_BAO"
    write_case(case_e, {
        "claim_amount": 61000000, "incident_date": "2015-03-04", "plate_number": "51A-555.55",
        "contact_phone": "0909000555", "repair_shop": "GARAGE-AI-DEMO-2",
    }, [
        "Metadata khai báo ảnh do AI tạo và có qua Adobe Photoshop.",
        "Ảnh đồng thời gần trùng case 04 vì hai file chỉ khác metadata.",
        "UI yêu cầu rà soát nguồn gốc; không tự kết luận gian lận.",
    ])
    copy_with_png_metadata(
        args.ai_unmarked, case_e / "01_anh_ai_co_marker.png",
        "AI generated with OpenAI image; edited with Adobe Photoshop; synthetic demo only",
    )

    case_f = output / "06_CLAIM_AI_CHINH_SUA"
    write_case(case_f, {
        "claim_amount": 69000000, "incident_date": "2015-03-05", "plate_number": "51A-666.66",
        "contact_phone": "0909000666", "repair_shop": "GARAGE-DEMO-01",
    }, [
        "Metadata khai báo ảnh đã qua AI/Photoshop.",
        "Bộ fingerprint hiện tại dự kiến nối ảnh này về ảnh gốc như near_duplicate; nếu biến đổi pixel mạnh hơn, matching vẫn có thể mất.",
        "Quan hệ vẫn đối chiếu được với các claim trước qua xưởng sửa chữa.",
    ])
    copy_with_png_metadata(
        args.ai_edited, case_f / "01_anh_xe_duoc_AI_chinh_sua.png",
        "Generative AI edited with OpenAI image; Adobe Photoshop workflow; synthetic demo only",
    )

    expected = {
        "run_order": [case.name for case in (case_a, case_b, case_c, case_d, case_e, case_f)],
        "capabilities": {
            "exact_reuse": "expected_detected",
            "resize_recompress_reuse": "expected_detected",
            "declared_ai_metadata": "expected_detected",
            "unmarked_ai_pixel_only": "expected_inconclusive",
            "ai_edited_with_declared_marker": "expected_metadata_detection_and_near_duplicate_on_this_fixture",
            "relationship_matching": "expected_detected_when phone/shop/plate is shared with an earlier claim",
        },
    }
    (output / "00_KET_QUA_TONG_HOP.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    readme = """# BỘ DEMO ẢNH AI, ẢNH CHỈNH SỬA VÀ QUAN HỆ CLAIM

Mở `http://127.0.0.1:8000/intake` và chạy các thư mục theo thứ tự 01 → 06.

Cho mỗi case:

1. Bấm **Dùng hồ sơ mẫu** để hệ thống tự nạp feature bảng; bạn không cần nhập JSON.
2. Chép các giá trị trong `THONG_TIN_NHAP.json` vào Số tiền, Ngày sự cố, Biển số, Số điện thoại và Xưởng sửa chữa.
3. Chọn file ảnh trong thư mục case. Riêng case 01 chọn thêm biên bản ở mục Chứng từ.
4. Bấm **Phân tích hồ sơ** đúng một lần và chờ Workbench mở.
5. Xem ba vùng: Hư hỏng/nguồn gốc ảnh, Quan hệ cần xem lại, và Tín hiệu cần xử lý.

Ý nghĩa:

- Case 02 kiểm tra tái sử dụng đúng cùng file ảnh.
- Case 03 kiểm tra ảnh cùng nguồn nhưng đã resize/nén lại.
- Case 04 cố ý là ảnh AI không marker: kết quả đúng là **chưa đủ bằng chứng**, không phải “ảnh thật”.
- Case 05 dùng cùng hình nhưng có metadata tự khai báo AI/phần mềm chỉnh sửa, nên vừa có marker vừa nối được về case 04.
- Case 06 là ảnh xe được AI chỉnh sửa. Marker cho biết workflow khai báo AI; matching pixel có thể mất nếu nội dung thay đổi nhiều.
- Quan hệ chỉ dùng dữ liệu có trước thời điểm chấm. Hai claim có cùng phone/shop/plate sẽ được nối, nhưng đây chỉ là tín hiệu rà soát.

Đây là dữ liệu tổng hợp phục vụ demo, không dùng làm bằng chứng nghiệp vụ hay đo chất lượng production.
"""
    (output / "00_DOC_TRUOC_KHI_DEMO.md").write_text(readme, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
