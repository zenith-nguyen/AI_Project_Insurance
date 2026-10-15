"""Build three presenter-friendly claim examples in the user's download folder."""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "prototype/demo_assets/synthetic_vehicle_collision.png"
SOURCE_DOCUMENT = ROOT / "prototype/demo_assets/synthetic_repair_estimate.png"


CASES = [
    {
        "folder": "01_HO_SO_DAY_DU",
        "title": "Hồ sơ đầy đủ — chạy toàn bộ model",
        "fields": (67140, "2015-02-28", "51A-111.11", "0909000111", "GARAGE-DEMO-01"),
        "files": [
            (SOURCE_IMAGE, "01_ANH_XE.png", "Ảnh xe"),
            (SOURCE_DOCUMENT, "02_CHUNG_TU.png", "Chứng từ"),
        ],
        "purpose": "Kiểm tra XGBoost, YOLO, authenticity, document pipeline, consistency, graph và Workbench trên cùng một claim.",
        "expected": "Các module có input phải completed; ảnh có overlay nếu YOLO phát hiện; chứng từ có kết quả đọc; quyết định lưu được vào lịch sử.",
    },
    {
        "folder": "02_ANH_TRUNG_VA_QUAN_HE",
        "title": "Ảnh tái sử dụng — số điện thoại và xưởng trùng",
        "fields": (52000, "2015-03-01", "51A-222.22", "+84 909 000 111", "Garage Demo 01"),
        "files": [
            (SOURCE_IMAGE, "01_ANH_XE_TAI_SU_DUNG.png", "Ảnh xe"),
        ],
        "purpose": "Kiểm tra exact reuse và entity normalization v2: +84 phải ghép với 0; tên xưởng khác dấu/cách viết vẫn được chuẩn hóa.",
        "expected": "Có tín hiệu ảnh xuất hiện ở claim trước và quan hệ dùng chung; thiếu chứng từ phải hiển thị rõ, không làm mất kết quả ảnh/XGBoost/graph.",
    },
    {
        "folder": "03_ANH_CO_DAU_VET_AI",
        "title": "Ảnh có metadata khai báo AI/chỉnh sửa",
        "fields": (61000, "2015-03-04", "51A-555.55", "0909000555", "GARAGE-AI-DEMO-02"),
        "files": [
            (SOURCE_IMAGE, "01_ANH_CO_MARKER_AI.png", "Ảnh xe"),
            (SOURCE_DOCUMENT, "02_CHUNG_TU.png", "Chứng từ"),
        ],
        "purpose": "Kiểm tra authenticity khi metadata khai báo AI generator và phần mềm chỉnh sửa, đồng thời vẫn chạy ảnh/chứng từ như bình thường.",
        "expected": "Nguồn gốc ảnh ở mức cần rà soát; UI nêu metadata AI và Photoshop làm căn cứ, nhưng không tự kết luận claim gian lận.",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8-sig")


def instructions(case: dict) -> str:
    amount, date, plate, phone, shop = case["fields"]
    uploads = "\n".join(f"- {role}: `{target}`" for _, target, role in case["files"])
    return f"""# {case['title']}

## Nhập trên giao diện

1. Mở `http://127.0.0.1:8000/?view=intake`.
2. Bấm **Dùng hồ sơ mẫu** để nút chuyển sang **Hồ sơ mẫu đang bật**.
3. Nhập Số tiền `{amount}`, Ngày sự cố `{date}`, Biển số `{plate}`.
4. Mở **Thông tin để tìm hồ sơ có liên quan**, nhập điện thoại `{phone}` và xưởng `{shop}`.
5. Chọn file:
{uploads}
6. Bấm **Phân tích hồ sơ** đúng một lần. Theo dõi trạng thái: chờ lượt → dữ liệu bảng → ảnh/chứng từ → quan hệ → tổng hợp.
7. Trong lúc job chạy, có thể mở Dashboard ở tab khác; job vẫn tiếp tục. Trên CPU, case có chứng từ có thể mất 2–4 phút ở lượt đầu.
8. Khi Workbench mở, xem các tab **Tổng quan**, **Ảnh & chứng từ**, **Quan hệ**, **Nhật ký**.
9. Nếu có cờ, kiểm tra biểu tượng **⚑** trên đúng tab và đúng ảnh/chứng từ/quan hệ gây ra cờ.
10. Mở **Chi tiết điểm xếp hạng và lý do chưa chấm**. Nếu không có điểm, UI phải nói rõ thiếu bao nhiêu trường, nhóm dữ liệu nào, phần nào vẫn chạy và việc cần làm.
11. Chọn một quyết định, ghi lý do ít nhất 3 từ và bấm **Lưu quyết định** để kiểm tra Nhật ký.

## Mục tiêu

{case['purpose']}

## Kết quả mong đợi

{case['expected']}

Đây là dữ liệu tổng hợp. Cờ kiểm tra chỉ dùng ưu tiên con người rà soát, không phải kết luận gian lận.
"""


def build(output: Path, *, refresh: bool = False) -> Path:
    if output.exists() and not refresh:
        raise FileExistsError(f"Không ghi đè thư mục đã có: {output}")
    missing = [str(source) for case in CASES for source, _, _ in case["files"] if not source.is_file()]
    if missing:
        raise FileNotFoundError("Thiếu fixture nguồn:\n" + "\n".join(missing))
    output.mkdir(parents=True, exist_ok=refresh)
    matrix = []
    for index, case in enumerate(CASES, start=1):
        folder = output / case["folder"]
        folder.mkdir(exist_ok=refresh)
        for source, target, _ in case["files"]:
            destination = folder / target
            if target == "01_ANH_CO_MARKER_AI.png":
                metadata = PngImagePlugin.PngInfo()
                metadata.add_text("Description", "AI generated with OpenAI image; edited with Adobe Photoshop; synthetic demo only")
                with Image.open(source) as image:
                    image.convert("RGB").save(destination, pnginfo=metadata)
            else:
                shutil.copy2(source, destination)
        amount, date, plate, phone, shop = case["fields"]
        write_text(folder / "00_HUONG_DAN_TEST.md", instructions(case))
        write_text(
            folder / "01_THONG_TIN_NHAP.txt",
            f"Dùng hồ sơ mẫu: BẬT\nSố tiền: {amount}\nNgày sự cố: {date}\nBiển số: {plate}\nSố điện thoại: {phone}\nXưởng sửa chữa: {shop}",
        )
        write_text(folder / "02_KET_QUA_MONG_DOI.txt", case["expected"])
        matrix.append({"STT": index, "Thư mục": case["folder"], "Mục tiêu": case["purpose"], "Kết quả mong đợi": case["expected"]})

    capture_folder = output / "99_TUY_CHON_TEST_PHIEN_CHUP_3_GOC"
    capture_folder.mkdir(exist_ok=refresh)
    with Image.open(SOURCE_IMAGE) as image:
        base = image.convert("RGB")
        variants = [base, base.transpose(Image.Transpose.FLIP_LEFT_RIGHT), base.crop((40, 20, base.width - 20, base.height - 40)).resize(base.size)]
        for index, variant in enumerate(variants, start=1):
            variant.save(capture_folder / f"GOC_{index}.jpg", quality=88)
    write_text(capture_folder / "00_CACH_TEST.md", """# TEST ẢNH CHỤP MỚI CÓ KIỂM SOÁT

Đây là bước tùy chọn để kiểm tra UX, không phải bộ ảnh camera thật.

1. Ở trang Nạp hồ sơ, nhập thông tin hoặc bật hồ sơ mẫu.
2. Mở **Ảnh chụp mới có kiểm soát** và bấm **Tạo yêu cầu chụp 3 góc**. Hệ thống tự lưu claim trước.
3. Chọn lần lượt `GOC_1.jpg`, `GOC_2.jpg`, `GOC_3.jpg`, rồi bấm **Lưu 3 ảnh vào hồ sơ**.
4. Thêm chứng từ nếu muốn và bấm **Phân tích hồ sơ**.

Kết quả đúng: UI hiện mã phiên/hạn giờ; Workbench ghi Guided capture đã chạy. Cơ chế này tăng khả năng truy vết ảnh mới, nhưng không tự chứng minh hiện trường thật.
""")

    write_text(output / "00_BAT_DAU_TU_DAY.md", """# BỘ 3 HỒ SƠ TEST — CHẠY THEO THỨ TỰ

1. Bảo đảm API đang chạy tại `http://127.0.0.1:8000/`.
2. Chạy thư mục `01`, sau đó `02`, rồi `03`. Thứ tự này cần thiết để case 02 tìm được ảnh và quan hệ của case 01.
3. Trong từng thư mục, mở `00_HUONG_DAN_TEST.md` và nhập đúng thông tin.
4. Luôn bật **Dùng hồ sơ mẫu** để XGBoost nhận đủ feature demo.
5. Sau mỗi case, quay lại Dashboard để xem thứ tự ưu tiên và lịch sử.
6. Khi đang chạy, UI phải hiện giai đoạn và số giây. Có thể mở Dashboard; trạng thái **Đang phân tích** phải xuất hiện.
7. Trong Workbench, lưu một quyết định rồi mở tab **Nhật ký**. Tab phải nói rõ ai, làm gì, lúc nào và vì sao.
8. Tab **Quan hệ** phải diễn giải hồ sơ nào liên quan, loại thông tin trùng, ý nghĩa và việc nên làm; số NetworkX nằm trong phần kỹ thuật.
9. Mã máy như `claim_document` không được xuất hiện ở phần nghiệp vụ. UI phải ghi rõ **Chứng từ bồi thường (biên bản, báo giá hoặc hóa đơn)**.
10. Cờ cần rà soát phải có biểu tượng **⚑** màu đỏ ở tab và ngay phần bằng chứng/quan hệ liên quan. Tín hiệu chỉ mang tính thông tin không được tính thành cờ.

## Thời gian

- Lượt đầu có YOLO + OCR + LayoutLMv3 trên CPU có thể mất khoảng 2–4 phút.
- Mở lại cùng hồ sơ khi bằng chứng/checkpoint không đổi sẽ dùng kết quả đã lưu và nhanh hơn nhiều.
- Thêm tệp mới làm cache hết hiệu lực để tránh trả kết quả cũ.

Thư mục `99_TUY_CHON_TEST_PHIEN_CHUP_3_GOC` dùng để thử yêu cầu chụp có thời hạn. Đây là bước tùy chọn.

Ba case lần lượt kiểm tra: luồng đầy đủ; ảnh tái sử dụng + graph; ảnh có metadata khai báo AI/chỉnh sửa.
""")
    with (output / "01_MA_TRAN_3_CASE.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matrix[0]))
        writer.writeheader()
        writer.writerows(matrix)

    inventory = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        inventory.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    exact_a = sha256(output / "01_HO_SO_DAY_DU/01_ANH_XE.png")
    exact_b = sha256(output / "02_ANH_TRUNG_VA_QUAN_HE/01_ANH_XE_TAI_SU_DUNG.png")
    manifest = {
        "schema_version": "1.1", "case_count": len(CASES), "run_order": [case["folder"] for case in CASES],
        "exact_reuse_pair_verified": exact_a == exact_b, "files": inventory,
    }
    (output / "99_MANIFEST_SHA256.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not manifest["exact_reuse_pair_verified"]:
        raise RuntimeError("Case 01/02 image hashes must be identical.")
    shutil.make_archive(str(output), "zip", root_dir=output.parent, base_dir=output.name)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--refresh", action="store_true", help="Cập nhật các file do script quản lý trong thư mục đã có.")
    args = parser.parse_args()
    print(build(args.output.resolve(), refresh=args.refresh))
