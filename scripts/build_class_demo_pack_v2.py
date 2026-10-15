"""Build a second, visually distinct three-claim classroom demo pack."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from build_class_demo_pack import add_ai_metadata, build_document, sha256, write_text


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "prototype" / "demo_assets" / "class_demo_v2_2026_10_15"


CASES = [
    {
        "folder": "01_HATCHBACK_CAM_HO_SO_DAY_DU",
        "title": "Hatchback cam — va chạm phía sau",
        "image": "orange_hatchback_rear_damage.png",
        "image_target": "01_ANH_XE_HATCHBACK_CAM.png",
        "document_target": "02_BAO_GIA_SUA_CHUA.png",
        "document_name": "Báo giá sửa chữa giả lập",
        "claim_amount": 31_600_000,
        "incident_date": "2026-10-09",
        "plate": "59H-246.81",
        "phone": "0936221100",
        "garage": "GARAGE-METRO-21",
        "damage": "Móp sâu cửa cốp sau, cản sau bung khỏi thân xe và đèn hậu trái bị vỡ",
        "purpose": "Trình diễn một hồ sơ đủ ảnh, chứng từ và thông tin để xem kết quả hư hỏng, đối chiếu và nhật ký.",
        "expected": "Các module đang sẵn sàng trả kết quả; ảnh và chứng từ nằm trong cùng hồ sơ; người duyệt có thể lưu quyết định.",
        "ai_marker": False,
    },
    {
        "folder": "02_VAN_TRANG_DOI_XE_CO_QUAN_HE",
        "title": "Van trắng — đội xe có quan hệ",
        "image": "white_van_side_damage.png",
        "image_target": "01_ANH_XE_VAN_TRANG.png",
        "document_target": "02_BIEN_BAN_DOI_XE.png",
        "document_name": "Biên bản tiếp nhận xe giả lập",
        "claim_amount": 24_900_000,
        "incident_date": "2026-10-10",
        "plate": "50D-615.37",
        "phone": "0936221100",
        "garage": "GARAGE-METRO-21",
        "damage": "Móp dài cửa trượt và hông phải, nhiều vết cạ ngang, vỏ gương phải bị vỡ",
        "purpose": "Trình diễn quan hệ hợp lệ có thể có trong đội xe: hồ sơ 01 và 02 dùng chung đầu mối liên hệ và xưởng nhưng là hai xe khác nhau.",
        "expected": "Tab Quan hệ chỉ ra hồ sơ 01 và loại dữ liệu dùng chung; đây là đầu mối đối chiếu chứ không phải kết luận gian lận.",
        "ai_marker": False,
    },
    {
        "folder": "03_SEDAN_XANH_DEN_NGUON_GOC_CAN_XEM",
        "title": "Sedan xanh đen — nguồn gốc cần xem",
        "image": "navy_sedan_front_glass_damage.png",
        "image_target": "01_ANH_XE_CO_KHAI_BAO_AI.png",
        "document_target": "02_PHIEU_KIEM_TRA_SO_BO.png",
        "document_name": "Phiếu kiểm tra sơ bộ giả lập",
        "claim_amount": 36_750_000,
        "incident_date": "2026-10-11",
        "plate": "61A-904.26",
        "phone": "0984332277",
        "garage": "GARAGE-LAKE-05",
        "damage": "Capo móp rộng, đèn trước phải vỡ, cản trước nứt và kính chắn gió có vết nứt lan",
        "purpose": "Trình diễn kiểm tra nguồn gốc ảnh bằng metadata tự khai báo AI/chỉnh sửa và cách hệ thống chuyển tín hiệu thành hành động nghiệp vụ.",
        "expected": "Ảnh bị gắn cờ cần rà soát với lý do cụ thể; hệ thống không tự suy diễn thành kết luận gian lận.",
        "ai_marker": True,
    },
]


def case_guide(case: dict) -> str:
    provenance = (
        "Ảnh có metadata khai báo AI/chỉnh sửa để hệ thống phát hiện căn cứ nguồn gốc."
        if case["ai_marker"]
        else "Ảnh tổng hợp không được gắn marker nguồn gốc; kết quả authenticity có thể là chưa đủ căn cứ."
    )
    return f"""# {case['title']}

## Cách chạy trên giao diện

1. Mở `http://127.0.0.1:8000/` và chọn **Nạp hồ sơ mới**.
2. Bật **Dùng hồ sơ mẫu** để backend cấp feature bảng. Người trình diễn không nhập JSON.
3. Nhập số tiền `{case['claim_amount']}`, ngày `{case['incident_date']}`, biển số `{case['plate']}`.
4. Nhập số điện thoại `{case['phone']}` và xưởng `{case['garage']}`.
5. Tải vào mục **Ảnh xe**: `{case['image_target']}`.
6. Tải vào mục **Chứng từ bồi thường**: `{case['document_target']}`.
7. Bấm **Phân tích hồ sơ** đúng một lần. Theo dõi từng module trong thanh tiến trình rồi mở Workbench.

## Nội dung thuyết trình

- **Loại chứng từ:** {case['document_name']}.
- **Mục đích:** {case['purpose']}
- **Kết quả mong đợi:** {case['expected']}
- **Nguồn gốc ảnh:** {provenance}
- **Giới hạn cần nói rõ:** model tạo tín hiệu và sắp xếp ưu tiên; quyết định nghiệp vụ cuối cùng do con người xác nhận.
"""


def build(output: Path, *, refresh: bool = False) -> Path:
    if output.exists() and not refresh:
        raise FileExistsError(f"Không ghi đè thư mục đã tồn tại: {output}")
    missing = [ASSET_ROOT / case["image"] for case in CASES if not (ASSET_ROOT / case["image"]).is_file()]
    if missing:
        raise FileNotFoundError("Thiếu ảnh nguồn:\n" + "\n".join(map(str, missing)))
    output.mkdir(parents=True, exist_ok=refresh)

    matrix: list[dict] = []
    for index, case in enumerate(CASES, start=1):
        folder = output / case["folder"]
        folder.mkdir(exist_ok=refresh)
        source = ASSET_ROOT / case["image"]
        image_target = folder / case["image_target"]
        if case["ai_marker"]:
            add_ai_metadata(source, image_target)
        else:
            shutil.copy2(source, image_target)
        build_document(case, folder / case["document_target"])
        write_text(folder / "00_HUONG_DAN_TEST.md", case_guide(case))
        write_text(
            folder / "01_THONG_TIN_NHAP.txt",
            f"Dùng hồ sơ mẫu: BẬT\nSố tiền: {case['claim_amount']}\nNgày sự cố: {case['incident_date']}\n"
            f"Biển số: {case['plate']}\nSố điện thoại: {case['phone']}\nXưởng sửa chữa: {case['garage']}",
        )
        matrix.append(
            {
                "STT": index,
                "Hồ sơ": case["folder"],
                "Tình huống": case["title"],
                "Giá trị trình diễn": case["purpose"],
                "Kết quả mong đợi": case["expected"],
            }
        )

    with (output / "01_MA_TRAN_3_HO_SO.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(matrix[0]))
        writer.writeheader()
        writer.writerows(matrix)

    provenance = {
        "pack_version": "class-demo-alternative-v2",
        "mode": "generate",
        "tool": "OpenAI image generation",
        "notice": "Mọi ảnh, chứng từ, danh tính và chi tiết hồ sơ đều là dữ liệu tổng hợp để trình diễn.",
        "prompt_record": "Xem 03_PROMPT_TAO_ANH.md",
    }
    (output / "02_NGUON_GOC_DU_LIEU_TONG_HOP.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(ASSET_ROOT / "README.md", output / "03_PROMPT_TAO_ANH.md")
    write_text(
        output / "00_BAT_DAU_TU_DAY.md",
        """# BỘ DEMO THAY THẾ V2 — 3 HỒ SƠ MỚI

Đây là bộ dữ liệu tổng hợp, không phải bằng chứng bảo hiểm thật và không có giá trị pháp lý.

## Thứ tự demo đề xuất

1. Mở `http://127.0.0.1:8000/` rồi chạy hồ sơ `01` để giới thiệu luồng đầy đủ.
2. Chạy hồ sơ `02` sau hồ sơ `01` để tab **Quan hệ** có lịch sử đối chiếu số điện thoại và xưởng.
3. Chạy hồ sơ `03` để trình diễn cờ nguồn gốc ảnh dựa trên metadata khai báo AI/chỉnh sửa.
4. Lưu một quyết định trong Workbench, sau đó mở **Danh sách hồ sơ → Lịch sử** để trình diễn audit log.

Mỗi thư mục hồ sơ có `00_HUONG_DAN_TEST.md` và `01_THONG_TIN_NHAP.txt`. Hãy bật **Dùng hồ sơ mẫu**; người dùng nghiệp vụ không phải nhập JSON.
""",
    )

    inventory = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "99_MANIFEST_SHA256.json"):
        inventory.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {"pack_version": "class-demo-alternative-v2", "case_count": len(CASES), "files": inventory}
    (output / "99_MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    built = build(args.output.resolve(), refresh=args.refresh)
    print(f"Demo pack: {built}")
    if args.make_zip:
        archive = Path(shutil.make_archive(str(built), "zip", root_dir=built.parent, base_dir=built.name))
        print(f"ZIP: {archive}")


if __name__ == "__main__":
    main()
