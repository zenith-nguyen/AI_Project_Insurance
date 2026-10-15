"""Build a business-oriented manual demo pack from the existing synthetic fixtures.

The generated pack is intentionally written for a non-technical presenter.  It
does not create new evidence; it copies the already prepared synthetic images
and documents and adds deterministic instructions, expectations and hashes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


SOURCE_FILES = {
    "original_image": Path("01_CLAIM_GOC/01_anh_xe_goc.png"),
    "document": Path("01_CLAIM_GOC/02_bien_ban_hien_truong.png"),
    "exact_reuse": Path("02_CLAIM_ANH_TRUNG/01_anh_xe_tai_su_dung_y_nguyen.png"),
    "near_duplicate": Path("03_CLAIM_ANH_NEN_RESIZE/01_anh_qua_mang_xa_hoi_gia_lap.jpg"),
    "ai_unmarked": Path("04_CLAIM_AI_KHONG_MARKER/01_anh_ai_khong_marker.png"),
    "ai_declared": Path("05_CLAIM_AI_CO_KHAI_BAO/01_anh_ai_co_marker.png"),
    "ai_edited": Path("06_CLAIM_AI_CHINH_SUA/01_anh_xe_duoc_AI_chinh_sua.png"),
}


CASES = [
    {
        "folder": "01_HO_SO_DAY_DU",
        "title": "Hồ sơ có ảnh, chứng từ và dữ liệu bảng",
        "demo_features": True,
        "fields": [67140, "2015-02-28", "51A-111.11", "0909000111", "GARAGE-DEMO-01"],
        "files": [("original_image", "01_anh_xe_hu_hong.png", "Ảnh xe"), ("document", "02_bien_ban_hien_truong.png", "Chứng từ")],
        "technical": "XGBoost có điểm xếp hạng; YOLO và document pipeline chạy nếu readiness đang active.",
        "business": "Người duyệt nhận một hồ sơ tổng hợp và biết phần nào đã kiểm tra, phần nào cần xác minh.",
        "action": "Mở Workbench, đọc vùng Hệ thống đã thấy → Vì sao cần quan tâm → Việc nên làm tiếp.",
        "pass": "Có kết quả phân tích; module thiếu phải hiện lý do cụ thể, không làm mất kết quả module khác.",
    },
    {
        "folder": "02_ANH_TAI_SU_DUNG_VA_QUAN_HE",
        "title": "Ảnh được dùng lại và thực thể dùng chung",
        "demo_features": True,
        "fields": [52000, "2015-03-01", "51A-222.22", "0909000111", "GARAGE-DEMO-01"],
        "files": [("exact_reuse", "01_anh_tai_su_dung_y_nguyen.png", "Ảnh xe")],
        "technical": "Hash ảnh trùng với case 01; phone và repair_shop cũng trùng với hồ sơ đã có trước đó.",
        "business": "Hệ thống đưa hồ sơ lên rà soát vì một bằng chứng hoặc đầu mối đã xuất hiện ở claim khác.",
        "action": "Mở danh sách hồ sơ liên quan; yêu cầu ảnh chụp mới nếu nghiệp vụ thấy cần.",
        "pass": "Có cảnh báo reuse exact và ít nhất một quan hệ lịch sử; không tự kết luận gian lận.",
    },
    {
        "folder": "03_ANH_QUA_NEN_RESIZE",
        "title": "Ảnh cùng nguồn sau resize/nén",
        "demo_features": True,
        "fields": [48000, "2015-03-02", "51A-333.33", "0909000333", "GARAGE-DEMO-01"],
        "files": [("near_duplicate", "01_anh_qua_nen_resize.jpg", "Ảnh xe")],
        "technical": "Fingerprint gần trùng được so với ảnh lịch sử dù byte và kích thước file đã đổi.",
        "business": "Giảm khả năng né kiểm tra reuse bằng cách tải lại ảnh qua ứng dụng hoặc mạng xã hội.",
        "action": "Đối chiếu ảnh gốc và hồ sơ liên quan trước khi quyết định.",
        "pass": "Có near-duplicate hoặc lý do rõ nếu ngưỡng chưa bắt được; xưởng dùng chung vẫn được graph ghi nhận.",
    },
    {
        "folder": "04_ANH_AI_KHONG_MARKER",
        "title": "Ảnh AI không có provenance/metadata khai báo",
        "demo_features": True,
        "fields": [73000, "2015-03-03", "51A-444.44", "0909000444", "GARAGE-AI-DEMO"],
        "files": [("ai_unmarked", "01_anh_ai_khong_marker.png", "Ảnh xe")],
        "technical": "Không có marker không đủ để chứng minh ảnh thật; pixel detector chưa được mở nếu chưa đạt benchmark.",
        "business": "Hệ thống tránh cho người duyệt cảm giác an toàn giả và đề nghị thu thập bằng chứng tốt hơn.",
        "action": "Xem checklist nguồn gốc; nếu cần, yêu cầu phiên chụp mới có hướng dẫn.",
        "pass": "UI ghi chưa đủ bằng chứng/inconclusive; tuyệt đối không ghi ảnh chắc chắn là thật.",
    },
    {
        "folder": "05_ANH_AI_CO_KHAI_BAO",
        "title": "Ảnh có metadata khai báo AI/chỉnh sửa",
        "demo_features": True,
        "fields": [61000, "2015-03-04", "51A-555.55", "0909000555", "GARAGE-AI-DEMO-2"],
        "files": [("ai_declared", "01_anh_ai_co_marker.png", "Ảnh xe")],
        "technical": "Metadata chứa marker khai báo AI/phần mềm chỉnh sửa và được trích thành căn cứ.",
        "business": "Người duyệt biết vì sao nguồn gốc ảnh cần được kiểm tra thêm thay vì chỉ nhận một nhãn đỏ.",
        "action": "Đối chiếu provenance và yêu cầu ảnh gốc nếu ảnh là bằng chứng trọng yếu.",
        "pass": "Checklist hiển thị dấu AI/chỉnh sửa cùng căn cứ; không tự suy ra claim gian lận.",
    },
    {
        "folder": "06_ANH_DUOC_AI_CHINH_SUA",
        "title": "Ảnh xe có workflow chỉnh sửa bằng AI",
        "demo_features": True,
        "fields": [69000, "2015-03-05", "51A-666.66", "0909000666", "GARAGE-DEMO-01"],
        "files": [("ai_edited", "01_anh_xe_duoc_ai_chinh_sua.png", "Ảnh xe")],
        "technical": "Marker chỉnh sửa được đọc; fingerprint và graph tiếp tục so với lịch sử nếu còn đủ tương đồng.",
        "business": "Tách câu hỏi ảnh đã chỉnh sửa khỏi kết luận gian lận và đưa ra hành động xác minh phù hợp.",
        "action": "Xem ảnh gốc/claim liên quan và yêu cầu ảnh chụp mới khi cần.",
        "pass": "UI nêu dấu vết nào đã thấy, dấu vết nào thiếu và giới hạn của phép kiểm tra.",
    },
    {
        "folder": "07_THIEU_CHUNG_TU",
        "title": "Chỉ có ảnh xe, thiếu chứng từ",
        "demo_features": True,
        "fields": [42000, "2015-03-06", "51A-777.77", "0909000777", "GARAGE-DEMO-07"],
        "files": [("ai_edited", "01_anh_xe.png", "Ảnh xe")],
        "technical": "XGBoost/ảnh/nguồn gốc vẫn chạy; document pipeline được đánh dấu skipped vì không có input.",
        "business": "Hồ sơ vẫn được xếp hàng nhưng người duyệt thấy rõ thiếu chứng từ nào cần bổ sung.",
        "action": "Chọn Yêu cầu bổ sung nếu chứng từ là bắt buộc theo quy trình.",
        "pass": "Có điểm nếu bật hồ sơ mẫu; bằng chứng hiển thị 2/3 loại thay vì 100% mơ hồ.",
    },
    {
        "folder": "08_CHI_CO_CHUNG_TU",
        "title": "Chỉ có chứng từ, chưa có ảnh xe",
        "demo_features": True,
        "fields": [36000, "2015-03-07", "51A-888.88", "0909000888", "GARAGE-DEMO-08"],
        "files": [("document", "01_bien_ban_hien_truong.png", "Chứng từ")],
        "technical": "Document pipeline chạy; damage/authenticity ảnh được đánh dấu skipped vì không có ảnh.",
        "business": "Không chặn toàn bộ hồ sơ; hệ thống vẫn đọc phần có sẵn và đề nghị bổ sung ảnh.",
        "action": "Kiểm tra trường OCR/KIE và yêu cầu ảnh tổn thất.",
        "pass": "Kết quả partial có lý do; không hiển thị xe không hư hỏng chỉ vì thiếu ảnh.",
    },
    {
        "folder": "09_KHONG_CO_FEATURE_BANG",
        "title": "Có ảnh/chứng từ nhưng không có feature XGBoost",
        "demo_features": False,
        "fields": [25000, "2015-03-08", "51A-999.99", "0909000999", "GARAGE-DEMO-09"],
        "files": [("original_image", "01_anh_xe.png", "Ảnh xe"), ("document", "02_chung_tu.png", "Chứng từ")],
        "technical": "Ảnh, tài liệu và graph vẫn chạy; XGBoost trả not_scored do thiếu schema feature đầy đủ.",
        "business": "Người dùng vẫn nộp file bình thường; hệ thống nghiệp vụ sau này sẽ tự cấp feature, không bắt họ nhập JSON.",
        "action": "Đọc các tín hiệu còn lại; bổ sung dữ liệu bảng từ core system nếu cần xếp hạng.",
        "pass": "UI ghi Chưa chấm và nguyên nhân thiếu feature; các module còn input vẫn có kết quả.",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8-sig")


def case_instructions(case: dict) -> str:
    amount, date, plate, phone, shop = case["fields"]
    uploads = "\n".join(f"- **{role}:** `{target}`" for _, target, role in case["files"])
    demo = "BẬT" if case["demo_features"] else "TẮT"
    return f"""# {case['title']}

## Thao tác trên một link

1. Mở `http://127.0.0.1:8000/`.
2. Chọn **Nạp hồ sơ mới** ở menu trái.
3. Đặt **Dùng hồ sơ mẫu: {demo}**.
4. Nhập Số tiền `{amount}`, Ngày sự cố `{date}`, Biển số `{plate}`.
5. Nhập Số điện thoại `{phone}` và Xưởng sửa chữa `{shop}`.
6. Chọn đúng file:
{uploads}
7. Bấm **Phân tích hồ sơ** một lần. Hệ thống tự mở Workbench.

## Kết quả cần đọc

- **Kỹ thuật:** {case['technical']}
- **Giá trị nghiệp vụ:** {case['business']}
- **Hành động đề xuất:** {case['action']}
- **Điều kiện PASS:** {case['pass']}

Các cảnh báo là tín hiệu ưu tiên rà soát, không phải kết luận gian lận hay căn cứ tự động từ chối bồi thường.
"""


def build(source: Path, output: Path) -> Path:
    resolved = {name: source / relative for name, relative in SOURCE_FILES.items()}
    missing = [str(path) for path in resolved.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Thiếu fixture nguồn:\n- " + "\n- ".join(missing))
    if output.exists():
        raise FileExistsError(f"Thư mục đã tồn tại, không ghi đè: {output}")
    output.mkdir(parents=True)

    matrix_rows = []
    expected = {"product_url": "http://127.0.0.1:8000/", "run_in_order": [], "cases": {}}
    for index, case in enumerate(CASES, start=1):
        folder = output / case["folder"]
        folder.mkdir()
        for source_key, target_name, _ in case["files"]:
            shutil.copy2(resolved[source_key], folder / target_name)
        write_text(folder / "00_THUC_HIEN_VA_KET_QUA.md", case_instructions(case))
        amount, date, plate, phone, shop = case["fields"]
        input_payload = {
            "use_demo_features": case["demo_features"],
            "claim_amount": amount,
            "incident_date": date,
            "plate_number": plate,
            "contact_phone": phone,
            "repair_shop": shop,
        }
        (folder / "01_DU_LIEU_NHAP.json").write_text(
            json.dumps(input_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        expected["run_in_order"].append(case["folder"])
        expected["cases"][case["folder"]] = {
            "title": case["title"], "technical": case["technical"],
            "business": case["business"], "action": case["action"], "pass": case["pass"],
        }
        matrix_rows.append({
            "STT": index, "Case": case["folder"], "Mục tiêu": case["title"],
            "Feature mẫu": "Bật" if case["demo_features"] else "Tắt",
            "Giá trị nghiệp vụ": case["business"], "Tiêu chí PASS": case["pass"],
        })

    start = """# BẮT ĐẦU TỪ ĐÂY — BỘ TEST DEMO NGHIỆP VỤ

Đây là dữ liệu tổng hợp, không chứa hồ sơ khách hàng thật. Chỉ dùng để demo và kiểm thử nghiên cứu.

## Chạy nhanh

1. Bảo đảm cửa sổ lệnh đang chạy API tại `http://127.0.0.1:8000/`.
2. Chỉ dùng **một link** trên. Dashboard, Nạp hồ sơ và Workbench nằm chung trong menu trái.
3. Chạy các thư mục `01` đến `09` theo thứ tự. Thứ tự tạo lịch sử để test reuse và graph.
4. Trong từng thư mục, mở `00_THUC_HIEN_VA_KET_QUA.md` và làm đúng các bước.
5. Quay lại **Danh sách hồ sơ** để xem hàng đợi, lịch sử và quyết định đã lưu.

## Khi demo trước lớp

- Case 01: cho thấy luồng end-to-end và từng module hoạt động độc lập khi thiếu input.
- Case 02–03: cho thấy giá trị chống tái sử dụng bằng chứng và nối quan hệ giữa claim.
- Case 04–06: cho thấy hệ thống kiểm tra nguồn gốc có căn cứ, đồng thời công khai giới hạn ảnh AI không marker.
- Case 07–09: cho thấy graceful degradation: thiếu chứng từ, ảnh hoặc feature vẫn phân tích phần còn lại.

Điểm XGBoost là điểm xếp hạng nghiên cứu để sắp hàng đợi, không phải xác suất gian lận. Cờ kiểm tra là lý do để con người xem kỹ hơn, không phải kết luận gian lận.
"""
    write_text(output / "00_BAT_DAU_TU_DAY.md", start)
    with (output / "01_MA_TRAN_TEST.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(matrix_rows[0]))
        writer.writeheader()
        writer.writerows(matrix_rows)
    (output / "02_KET_QUA_MONG_DOI.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_text(output / "03_KICH_BAN_TRINH_BAY.md", """# KỊCH BẢN TRÌNH BÀY 5 PHÚT

1. Mở Dashboard: giải thích đây là hàng đợi nghiệp vụ, sắp theo mức cần xử lý.
2. Nạp case 01: người dùng chỉ nhập thông tin cơ bản và tải file; không nhập JSON.
3. Mở Workbench: đọc ba cột Phát hiện → Ý nghĩa → Hành động.
4. Nạp case 02: chỉ ra ảnh trùng và thực thể dùng chung với claim trước.
5. Nạp case 04 hoặc 05: phân biệt “không tìm thấy marker” với “có bằng chứng khai báo AI”.
6. Lưu một quyết định của người duyệt rồi quay lại Dashboard để mở lịch sử.
7. Mở Chứng minh hệ thống: nêu checkpoint local, metric, hash, giới hạn và giá trị nghiệp vụ.

Câu kết: hệ thống hỗ trợ ưu tiên và gom bằng chứng cho người duyệt; quyết định cuối cùng vẫn thuộc về con người.
""")

    inventory = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        inventory.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {"pack_version": "business-demo-v2", "case_count": len(CASES), "files": inventory}
    (output / "99_MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    args = parser.parse_args()
    built = build(args.source_pack.resolve(), args.output.resolve())
    print(f"Demo pack: {built}")
    if args.make_zip:
        archive = Path(shutil.make_archive(str(built), "zip", root_dir=built.parent, base_dir=built.name))
        print(f"ZIP: {archive}")


if __name__ == "__main__":
    main()
