"""Build a polished, clearly synthetic Vietnamese motor-claim demo pack."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, PngImagePlugin

from build_class_demo_pack import fit_text, font, sha256, write_text


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "prototype" / "demo_assets" / "class_demo_v3_2026_10_16"
OLD_ASSETS = ROOT / "prototype" / "demo_assets" / "class_demo_v2_2026_10_15"

CASES = [
    {
        "folder": "01_SEDAN_XANH_DAU_VET_AI_VA_BIEN_SO",
        "title": "Sedan xanh đen — kiểm tra nguồn gốc và biển số",
        "image_source": ASSETS / "navy_sedan_plate_51K48276.png",
        "image_target": "01_ANH_XE_SEDAN_XANH.png",
        "document_target": "02_THONG_BAO_TON_THAT.png",
        "document_type": "THÔNG BÁO TỔN THẤT VÀ YÊU CẦU BỒI THƯỜNG",
        "form_code": "ATLAB-MO-01/2026",
        "claim_amount": 42_680_000,
        "incident_date": "2026-10-12",
        "plate": "51K-482.76",
        "phone": "0908123456",
        "garage": "XUONG-AN-PHU-DEMO",
        "policy": "ATD-MO-2026-10482",
        "insured": "NGUYỄN AN DEMO",
        "vehicle": "Sedan 5 chỗ, màu xanh đen",
        "location": "Đường nội bộ Khu đô thị Minh An (giả lập)",
        "damage": "Kính trước nứt; capo biến dạng; cụm đèn và cản trước hư hỏng sau va chạm.",
        "ai_marker": True,
        "purpose": "Minh họa ảnh có metadata khai báo AI/chỉnh sửa, OCR biển số và khoanh vùng hư hỏng.",
        "expected": "Nguồn gốc ảnh có cờ đỏ dựa trên metadata; biển số có thể được OCR rồi đối chiếu với thông tin khai báo.",
    },
    {
        "folder": "02_HATCHBACK_CAM_CO_QUAN_HE",
        "title": "Hatchback cam — đối chiếu quan hệ hồ sơ",
        "image_source": OLD_ASSETS / "orange_hatchback_rear_damage.png",
        "image_target": "01_ANH_XE_HATCHBACK_CAM.png",
        "document_target": "02_BIEN_BAN_GIAM_DINH.png",
        "document_type": "BIÊN BẢN GIÁM ĐỊNH TỔN THẤT XE CƠ GIỚI",
        "form_code": "ATLAB-GD-03/2026",
        "claim_amount": 31_600_000,
        "incident_date": "2026-10-13",
        "plate": "59N-317.84",
        "phone": "0908123456",
        "garage": "XUONG-AN-PHU-DEMO",
        "policy": "ATD-MO-2026-11207",
        "insured": "TRẦN MINH DEMO",
        "vehicle": "Hatchback 5 chỗ, màu cam",
        "location": "Bãi xe Trung tâm thương mại Đông Thành (giả lập)",
        "damage": "Cửa hậu móp sâu; cản sau bung; đèn hậu trái vỡ và trầy bề mặt sơn.",
        "ai_marker": False,
        "purpose": "Minh họa graph tìm hồ sơ trước dùng chung số điện thoại và xưởng sửa chữa.",
        "expected": "Tab Quan hệ chỉ ra hồ sơ 01 và giải thích rõ đây là đầu mối kiểm tra, không phải kết luận gian lận.",
    },
    {
        "folder": "03_VAN_TRANG_BAO_GIA_SUA_CHUA",
        "title": "Van trắng — báo giá sửa chữa và OCR chứng từ",
        "image_source": OLD_ASSETS / "white_van_side_damage.png",
        "image_target": "01_ANH_XE_VAN_TRANG.png",
        "document_target": "02_BAO_GIA_SUA_CHUA.png",
        "document_type": "BÁO GIÁ SỬA CHỮA XE CƠ GIỚI",
        "form_code": "ATLAB-RP-08/2026",
        "claim_amount": 27_450_000,
        "incident_date": "2026-10-14",
        "plate": "61C-908.52",
        "phone": "0914777888",
        "garage": "XUONG-MEKONG-DEMO",
        "policy": "ATD-MO-2026-11931",
        "insured": "CÔNG TY VẬN TẢI DEMO",
        "vehicle": "Van chở hàng, màu trắng",
        "location": "Kho hàng Khu công nghiệp Nam Sông (giả lập)",
        "damage": "Hông phải móp dài; cửa trượt trầy; vỏ gương phải vỡ và cần cân chỉnh thân vỏ.",
        "ai_marker": False,
        "purpose": "Minh họa OCR/KIE đọc ngày và tổng tiền trên một chứng từ có bố cục nghiệp vụ.",
        "expected": "Chứng từ được lưu, phân loại và trích xuất trường nếu document pipeline sẵn sàng; người duyệt xác nhận hoặc sửa.",
    },
]


def _money(value: int) -> str:
    return f"{value:,.0f}".replace(",", ".") + " VNĐ"


def _field(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str, width: int = 1020) -> int:
    draw.text((x, y), label.upper(), font=font(18, True), fill="#607276")
    draw.text((x + 285, y - 4), value, font=font(24), fill="#132f35")
    draw.line((x, y + 43, x + width, y + 43), fill="#d6e0df", width=2)
    return y + 64


def build_document(case: dict, target: Path) -> None:
    page = Image.new("RGB", (1240, 1754), "#fffefb")
    draw = ImageDraw.Draw(page)
    ink, teal, muted, red = "#123138", "#08766d", "#64767a", "#b42318"
    draw.rectangle((0, 0, 1240, 26), fill=teal)
    draw.rounded_rectangle((72, 58, 204, 166), radius=18, fill="#dff3ef", outline=teal, width=3)
    draw.text((102, 81), "AT", font=font(43, True), fill=teal)
    draw.text((235, 65), "BẢO HIỂM AN TÂM LAB", font=font(33, True), fill=ink)
    draw.text((237, 112), "Đơn vị mô phỏng nghiệp vụ · Không phải doanh nghiệp thật", font=font(18), fill=muted)
    draw.text((945, 70), case["form_code"], font=font(17, True), fill=muted)
    draw.text((945, 106), "Bản demo 01", font=font(17), fill=muted)
    draw.line((72, 193, 1168, 193), fill="#b7ceca", width=3)

    draw.text((620, 235), case["document_type"], anchor="ma", font=font(31, True), fill=ink)
    draw.text((620, 286), "DỮ LIỆU TỔNG HỢP · KHÔNG CÓ GIÁ TRỊ PHÁP LÝ", anchor="ma", font=font(20, True), fill=red)
    draw.text((620, 321), "Dùng để trình diễn hệ thống hỗ trợ rà soát hồ sơ bồi thường", anchor="ma", font=font(17), fill=muted)

    y = 376
    y = _field(draw, 95, y, "Số hợp đồng", case["policy"])
    y = _field(draw, 95, y, "Người được bảo hiểm", case["insured"])
    y = _field(draw, 95, y, "Xe / biển kiểm soát", f"{case['vehicle']}  ·  {case['plate']}")
    y = _field(draw, 95, y, "Ngày, nơi xảy ra", f"{case['incident_date']}  ·  {case['location']}")
    y = _field(draw, 95, y, "Đơn vị tiếp nhận", case["garage"])
    y = _field(draw, 95, y, "Điện thoại liên hệ", case["phone"])

    draw.rounded_rectangle((82, y + 13, 1158, y + 225), radius=16, fill="#edf7f5", outline="#bddbd6", width=2)
    draw.text((108, y + 40), "MÔ TẢ SỰ CỐ VÀ TỔN THẤT GHI NHẬN", font=font(21, True), fill=teal)
    line_y = y + 87
    narrative = f"Theo thông tin khai báo: {case['damage']} Phạm vi và nguyên nhân cuối cùng cần giám định viên xác nhận trên ảnh gốc và hồ sơ liên quan."
    for line in fit_text(draw, narrative, 980, size=25):
        draw.text((108, line_y), line, font=font(25), fill=ink)
        line_y += 36

    table_y = y + 270
    draw.rectangle((82, table_y, 1158, table_y + 63), fill=teal)
    draw.text((104, table_y + 18), "HẠNG MỤC DỰ KIẾN", font=font(20, True), fill="white")
    draw.text((886, table_y + 18), "THÀNH TIỀN", font=font(20, True), fill="white")
    values = [
        ("Kiểm tra, tháo lắp và đo kiểm", round(case["claim_amount"] * 0.12)),
        ("Phục hồi thân vỏ / phụ tùng", round(case["claim_amount"] * 0.58)),
        ("Sơn, cân chỉnh và kiểm tra hoàn thiện", case["claim_amount"] - round(case["claim_amount"] * 0.70)),
    ]
    row_y = table_y + 82
    for label, value in values:
        draw.text((104, row_y), label, font=font(23), fill=ink)
        draw.text((888, row_y), _money(value), font=font(23), fill=ink)
        draw.line((100, row_y + 43, 1140, row_y + 43), fill="#d8e1df", width=2)
        row_y += 72
    draw.text((722, row_y + 16), "TỔNG GIÁ TRỊ ĐỀ NGHỊ", font=font(20, True), fill=muted)
    draw.text((855, row_y + 57), _money(case["claim_amount"]), font=font(30, True), fill=teal)

    sig_y = row_y + 138
    draw.text((145, sig_y), "NGƯỜI KHAI BÁO", font=font(18, True), fill=ink)
    draw.text((515, sig_y), "GIÁM ĐỊNH VIÊN", font=font(18, True), fill=ink)
    draw.text((895, sig_y), "ĐƠN VỊ TIẾP NHẬN", font=font(18, True), fill=ink)
    draw.text((122, sig_y + 36), "Ký, ghi rõ họ tên (demo)", font=font(16), fill=muted)
    draw.text((500, sig_y + 36), "Ký, ghi rõ họ tên (demo)", font=font(16), fill=muted)
    draw.text((886, sig_y + 36), "Ký, đóng dấu (demo)", font=font(16), fill=muted)
    draw.text((620, 1687), "TÀI LIỆU TỔNG HỢP — KHÔNG DÙNG CHO GIAO DỊCH, BỒI THƯỜNG HOẶC XÁC MINH DANH TÍNH", anchor="ma", font=font(15, True), fill=red)

    page.save(target, optimize=True)
    page.save(target.with_suffix(".pdf"), "PDF", resolution=150.0)


def copy_vehicle(case: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if case["ai_marker"]:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("description", "AI generated synthetic insurance classroom demo; not real evidence")
        metadata.add_text("software", "OpenAI image generator; synthetic plate edit")
        metadata.add_text("usage", "Research demonstration only")
        with Image.open(case["image_source"]) as image:
            image.convert("RGB").save(target, pnginfo=metadata, optimize=True)
    else:
        shutil.copy2(case["image_source"], target)


def case_guide(case: dict, order: int) -> str:
    marker = "Có metadata khai báo AI để chứng minh một cờ có căn cứ." if case["ai_marker"] else "Không gắn marker AI; hệ thống phải trả kết quả chưa đủ căn cứ nếu không có dấu vết khác."
    return f"""# {case['title']}

## Dữ liệu nhập trên màn hình

- Bật **Dùng hồ sơ mẫu** để XGBoost có đủ feature nghiên cứu. Người dùng không nhập JSON.
- Số tiền: `{case['claim_amount']}`
- Ngày sự cố: `{case['incident_date']}`
- Biển số: `{case['plate']}`
- Số điện thoại: `{case['phone']}`
- Xưởng sửa chữa: `{case['garage']}`
- Ảnh xe: `{case['image_target']}`
- Chứng từ: `{case['document_target']}` (ưu tiên PNG để demo nhanh hơn PDF)

## Thứ tự thao tác

1. Mở `http://127.0.0.1:8000/` → **Nạp hồ sơ mới**.
2. Nhập các giá trị ở trên, chọn đúng ảnh và chứng từ rồi bấm **Phân tích hồ sơ** đúng một lần.
3. Trong Workbench, mở lần lượt **Tổng quan**, **Ảnh & chứng từ**, **Quan hệ**, **Nhật ký**.
4. Lưu một quyết định có lý do để chứng minh audit trail.

## Điều cần nói khi trình bày

- Mục đích: {case['purpose']}
- Kỳ vọng: {case['expected']}
- Nguồn gốc ảnh: {marker}
- Cờ, vùng khoanh, OCR và điểm xếp hạng chỉ hỗ trợ người duyệt; không tự kết luận gian lận hay tự từ chối bồi thường.
"""


def build(output: Path, *, refresh: bool = False) -> Path:
    if output.exists() and not refresh:
        raise FileExistsError(f"Thư mục đã tồn tại: {output}")
    missing = [Path(case["image_source"]) for case in CASES if not Path(case["image_source"]).is_file()]
    if missing:
        raise FileNotFoundError("Thiếu ảnh nguồn:\n" + "\n".join(map(str, missing)))
    output.mkdir(parents=True, exist_ok=refresh)

    matrix: list[dict] = []
    for order, case in enumerate(CASES, start=1):
        folder = output / case["folder"]
        folder.mkdir(exist_ok=refresh)
        copy_vehicle(case, folder / case["image_target"])
        build_document(case, folder / case["document_target"])
        write_text(folder / "00_HUONG_DAN_CHAY.md", case_guide(case, order))
        write_text(folder / "01_THONG_TIN_NHAP.txt", (
            f"Dùng hồ sơ mẫu: BẬT\nSố tiền: {case['claim_amount']}\nNgày sự cố: {case['incident_date']}\n"
            f"Biển số: {case['plate']}\nSố điện thoại: {case['phone']}\nXưởng sửa chữa: {case['garage']}"
        ))
        (folder / "claim_reference.json").write_text(json.dumps({
            "notice": "Tệp tham chiếu cho dev/QA; người dùng nghiệp vụ không cần tải JSON lên giao diện.",
            "claim_amount": case["claim_amount"], "incident_date": case["incident_date"],
            "plate_number": case["plate"], "relationship_entities": {
                "contact_phone": case["phone"], "repair_shop": case["garage"]
            }
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        matrix.append({"STT": order, "Hồ sơ": case["folder"], "Mục đích": case["purpose"], "Kết quả mong đợi": case["expected"]})

    with (output / "01_MA_TRAN_DEMO.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(matrix[0]))
        writer.writeheader(); writer.writerows(matrix)
    write_text(output / "00_BAT_DAU_TU_DAY.md", """# BỘ DEMO HỒ SƠ BẢO HIỂM VIỆT NAM — V3

Toàn bộ dữ liệu là **tổng hợp**, được thiết kế giống quy trình nghiệp vụ để trình diễn sản phẩm; không phải mẫu của một doanh nghiệp thật và không có giá trị pháp lý.

## Kịch bản 5–7 phút

1. Chạy hồ sơ `01` để xem nguồn gốc ảnh, OCR biển số, vùng hư hỏng và chứng từ.
2. Chạy hồ sơ `02` ngay sau hồ sơ 01 để graph phát hiện số điện thoại và xưởng dùng chung.
3. Chạy hồ sơ `03` nếu cần minh họa chứng từ khác và trường hợp OCR biển số không đủ tin cậy.
4. Lưu quyết định, mở **Nhật ký**, sau đó mở **Danh sách hồ sơ** để xem hàng đợi và lịch sử.

Lần chạy đầu trên CPU có thể chậm vì phải nạp PaddleOCR/LayoutLMv3. Chạy lại cùng file sẽ dùng cache. Chỉ tải file PNG chứng từ khi demo; PDF là bản để xem hoặc gửi báo cáo.
""")
    inventory = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "99_MANIFEST_SHA256.json"):
        inventory.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (output / "99_MANIFEST_SHA256.json").write_text(json.dumps({
        "pack_version": "vn-claim-demo-v3", "case_count": len(CASES),
        "notice": "Synthetic classroom data only", "files": inventory,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    args = parser.parse_args()
    built = build(args.output.resolve(), refresh=args.refresh)
    print(f"Demo pack: {built}")
    if args.make_zip:
        print("ZIP:", shutil.make_archive(str(built), "zip", root_dir=built.parent, base_dir=built.name))


if __name__ == "__main__":
    main()
