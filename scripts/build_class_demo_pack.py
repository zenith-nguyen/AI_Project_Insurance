"""Build a fresh, presenter-friendly synthetic claim demo pack.

The source vehicle images are synthetic.  The documents, identities and claim
details generated here are fictional and visibly marked as demo material.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "prototype" / "demo_assets" / "class_demo_2026_10_15"


CASES = [
    {
        "folder": "01_SUV_DO_HO_SO_DAY_DU",
        "title": "SUV đỏ — hồ sơ đầy đủ",
        "image": "red_suv_rear_left_damage.png",
        "image_target": "01_ANH_XE_SUV_DO.png",
        "document_target": "02_PHIEU_DU_TOAN_SUA_CHUA.png",
        "claim_amount": 38_450_000,
        "incident_date": "2026-10-12",
        "plate": "51K-482.16",
        "phone": "0908123456",
        "garage": "GARAGE-SUNRISE-07",
        "damage": "Móp cửa sau trái, trầy vòm bánh, nứt cụm đèn hậu",
        "purpose": "Trình diễn luồng đầy đủ: xếp hạng hồ sơ, khoanh vùng hư hỏng, đọc chứng từ, đối chiếu và lưu quyết định.",
        "expected": "Có kết quả cho mọi module đã cài; ảnh và chứng từ được hiển thị cùng một claim; người duyệt lưu được quyết định vào Nhật ký.",
        "ai_marker": False,
    },
    {
        "folder": "02_SEDAN_XANH_CO_QUAN_HE",
        "title": "Sedan xanh — có đầu mối dùng chung",
        "image": "blue_sedan_side_damage.png",
        "image_target": "01_ANH_XE_SEDAN_XANH.png",
        "document_target": "02_BIEN_NHAN_TIEP_NHAN_XE.png",
        "claim_amount": 27_800_000,
        "incident_date": "2026-10-13",
        "plate": "60A-731.25",
        "phone": "0908123456",
        "garage": "GARAGE-SUNRISE-07",
        "damage": "Móp hai cửa bên phải, trầy bệ cửa, vỡ ốp gương",
        "purpose": "Trình diễn graph: hồ sơ mới dùng chung số điện thoại và xưởng với hồ sơ 01 nhưng dùng ảnh và xe khác.",
        "expected": "Tab Quan hệ chỉ ra hồ sơ 01, hai loại thông tin trùng và hành động đối chiếu; hệ thống không tự kết luận gian lận.",
        "ai_marker": False,
    },
    {
        "folder": "03_PICKUP_BAC_CO_DAU_VET_AI",
        "title": "Pickup bạc — ảnh tổng hợp có khai báo",
        "image": "silver_pickup_front_left_damage.png",
        "image_target": "01_ANH_XE_CO_METADATA_AI.png",
        "document_target": "02_PHIEU_GIAM_DINH_HU_HONG.png",
        "claim_amount": 44_200_000,
        "incident_date": "2026-10-14",
        "plate": "43C-908.52",
        "phone": "0914777888",
        "garage": "GARAGE-RIVER-12",
        "damage": "Móp tai xe trước trái, vỡ đèn trước, nứt cản và cong mép capo",
        "purpose": "Trình diễn kiểm tra nguồn gốc: metadata tự khai báo AI/chỉnh sửa phải trở thành căn cứ cần rà soát.",
        "expected": "Nguồn gốc ảnh ở mức cần rà soát và nêu đúng metadata làm lý do; không biến tín hiệu này thành kết luận claim gian lận.",
        "ai_marker": True,
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    windows = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    linux = Path("/usr/share/fonts/truetype/dejavu") / (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    )
    return ImageFont.truetype(str(windows if windows.is_file() else linux), size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8-sig")


def fit_text(draw: ImageDraw.ImageDraw, text: str, box_width: int, *, size: int = 28) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    selected = font(size)
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=selected)[2] <= box_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_document(case: dict, target: Path) -> None:
    image = Image.new("RGB", (1240, 1754), "#fbfaf6")
    draw = ImageDraw.Draw(image)
    ink, muted, teal, red = "#173238", "#667a7d", "#0f766e", "#b42318"
    draw.rectangle((0, 0, 1240, 28), fill=teal)
    draw.text((78, 72), "HỒ SƠ BỒI THƯỜNG GIẢ LẬP", font=font(45, True), fill=ink)
    draw.text((80, 140), "DỮ LIỆU DEMO — KHÔNG CÓ GIÁ TRỊ PHÁP LÝ", font=font(24, True), fill=red)
    draw.line((78, 212, 1162, 212), fill="#b9cac7", width=3)

    rows = [
        ("Mã tình huống", case["folder"]),
        ("Ngày sự cố", case["incident_date"]),
        ("Biển số giả lập", case["plate"]),
        ("Số liên hệ giả lập", case["phone"]),
        ("Xưởng tiếp nhận", case["garage"]),
        ("Số tiền yêu cầu", f"{case['claim_amount']:,} VND"),
    ]
    y = 268
    for label, value in rows:
        draw.text((84, y), label.upper(), font=font(20, True), fill=muted)
        draw.text((395, y - 4), str(value), font=font(29), fill=ink)
        draw.line((84, y + 50, 1156, y + 50), fill="#dce5e3", width=2)
        y += 82

    draw.rounded_rectangle((78, 792, 1162, 1030), radius=18, fill="#eaf4f2", outline="#b9d8d3", width=2)
    draw.text((108, 826), "MÔ TẢ HƯ HỎNG KHAI BÁO", font=font(22, True), fill=teal)
    line_y = 880
    for line in fit_text(draw, case["damage"], 990, size=31):
        draw.text((108, line_y), line, font=font(31), fill=ink)
        line_y += 44

    items = [
        ("Kiểm tra và tháo lắp", round(case["claim_amount"] * 0.12)),
        ("Phụ tùng / phục hồi bề mặt", round(case["claim_amount"] * 0.58)),
        ("Sơn, cân chỉnh và kiểm tra", case["claim_amount"] - round(case["claim_amount"] * 0.70)),
    ]
    draw.rectangle((78, 1080, 1162, 1148), fill=teal)
    draw.text((104, 1097), "HẠNG MỤC GIẢ LẬP", font=font(22, True), fill="white")
    draw.text((880, 1097), "DỰ TOÁN", font=font(22, True), fill="white")
    y = 1178
    for label, amount in items:
        draw.text((104, y), label, font=font(25), fill=ink)
        draw.text((895, y), f"{amount:,}", font=font(25), fill=ink)
        draw.line((100, y + 49, 1140, y + 49), fill="#d9e2e0", width=2)
        y += 88
    draw.text((744, 1472), "TỔNG DỰ TOÁN", font=font(23, True), fill=muted)
    draw.text((824, 1520), f"{case['claim_amount']:,} VND", font=font(34, True), fill=teal)
    draw.text((78, 1668), "Tất cả tên, số điện thoại, biển số, số tiền và chữ ký trong tài liệu này đều là dữ liệu tổng hợp.", font=font(17), fill=muted)
    image.save(target, optimize=True)


def add_ai_metadata(source: Path, target: Path) -> None:
    metadata = PngImagePlugin.PngInfo()
    # Lower-case keys are intentional: Pillow exposes PNG text keys verbatim,
    # while the local analyzer reads the normalized description/software keys.
    metadata.add_text("description", "AI generated synthetic insurance demo; edited with Adobe Photoshop; not real evidence")
    metadata.add_text("software", "OpenAI image generator; Adobe Photoshop demo workflow")
    metadata.add_text("usage", "Classroom demonstration only")
    with Image.open(source) as image:
        image.convert("RGB").save(target, pnginfo=metadata, optimize=True)


def shifted(mask: Image.Image, dx: int, dy: int = 0) -> Image.Image:
    result = Image.new("L", mask.size, 0)
    result.paste(mask, (dx, dy))
    return result


def mask_iou(left: Image.Image, right: Image.Image) -> float:
    a = left.point(lambda value: 255 if value else 0)
    b = right.point(lambda value: 255 if value else 0)
    intersection = ImageChops.multiply(a, b).histogram()[255]
    union = ImageChops.lighter(a, b).histogram()[255]
    return intersection / union if union else 0.0


def closest_shift(mask: Image.Image, target: float) -> tuple[Image.Image, float, int]:
    candidates = []
    for dx in range(1, max(2, mask.width // 5)):
        candidate = shifted(mask, dx)
        score = mask_iou(mask, candidate)
        candidates.append((abs(score - target), candidate, score, dx))
        if score < target - 0.03:
            break
    _, candidate, score, dx = min(candidates, key=lambda item: item[0])
    return candidate, score, dx


def overlay(base: Image.Image, mask: Image.Image, color: tuple[int, int, int], alpha: int = 115) -> Image.Image:
    canvas = base.convert("RGBA")
    paint = Image.new("RGBA", base.size, color + (0,))
    paint.putalpha(mask.point(lambda value: alpha if value else 0))
    return Image.alpha_composite(canvas, paint).convert("RGB")


def panel(image: Image.Image, title: str, subtitle: str) -> Image.Image:
    fitted = ImageOps.fit(image.convert("RGB"), (680, 500), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (720, 610), "white")
    canvas.paste(fitted, (20, 82))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 17), title, font=font(27, True), fill="#153238")
    draw.text((20, 51), subtitle, font=font(18), fill="#5d7478")
    return canvas


def build_iou_explainer(source: Path, output: Path, *, refresh: bool = False) -> dict:
    output.mkdir(exist_ok=refresh)
    with Image.open(source) as opened:
        original = opened.convert("RGB")
    width, height = original.size
    # Illustrative manual polygon around the rear-left damage.  It is teaching
    # material, not a label used in a reported benchmark.
    points = [
        (int(width * 0.31), int(height * 0.31)),
        (int(width * 0.73), int(height * 0.34)),
        (int(width * 0.76), int(height * 0.66)),
        (int(width * 0.62), int(height * 0.81)),
        (int(width * 0.37), int(height * 0.75)),
        (int(width * 0.27), int(height * 0.53)),
    ]
    ground_truth = Image.new("L", original.size, 0)
    ImageDraw.Draw(ground_truth).polygon(points, fill=255)
    high, high_iou, high_dx = closest_shift(ground_truth, 0.95)
    low, low_iou, low_dx = closest_shift(ground_truth, 0.52)

    original.save(output / "01_ANH_GOC.png", optimize=True)
    overlay(original, ground_truth, (18, 166, 96)).save(output / "02_NHAN_CHUAN_NGUOI_VE.png", optimize=True)
    overlay(original, high, (245, 158, 11)).save(output / "03_DU_DOAN_GAN_TRUNG_NHAN_CHUAN.png", optimize=True)

    def comparison(prediction: Image.Image) -> Image.Image:
        gt_only = ImageChops.subtract(ground_truth, prediction)
        pred_only = ImageChops.subtract(prediction, ground_truth)
        both = ImageChops.multiply(ground_truth, prediction)
        result = overlay(original, gt_only, (37, 99, 235), 145)
        result = overlay(result, pred_only, (245, 158, 11), 145)
        return overlay(result, both, (18, 166, 96), 145)

    explainer = Image.new("RGB", (1460, 1240), "#f2f7f6")
    panels = [
        panel(original, "1. Ảnh gốc", "Chưa có đáp án vùng hư hỏng"),
        panel(overlay(original, ground_truth, (18, 166, 96)), "2. Nhãn chuẩn", "Vùng xanh do người gán nhãn vẽ và QA"),
        panel(comparison(high), f"3. Dự đoán tốt — IoU {high_iou:.3f}", "Xanh: trùng · xanh dương/cam: phần lệch"),
        panel(comparison(low), f"4. Dự đoán lệch — IoU {low_iou:.3f}", "Vùng khoanh lệch nhiều nên IoU giảm"),
    ]
    for index, item in enumerate(panels):
        explainer.paste(item, (10 + (index % 2) * 725, 10 + (index // 2) * 615))
    explainer.save(output / "04_IOU_MINH_HOA_4_BUOC.png", optimize=True)

    label = {
        "notice": "Nhãn minh họa do script tạo để giảng giải; không thuộc test set và không dùng báo cáo metric.",
        "class": "damage_region",
        "image_size": [width, height],
        "polygon": points,
        "high_example": {"shift_x": high_dx, "iou": high_iou},
        "low_example": {"shift_x": low_dx, "iou": low_iou},
    }
    (output / "05_NHAN_MINH_HOA.json").write_text(json.dumps(label, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_text(output / "00_DOC_TRUOC.md", f"""# NHÃN CHUẨN VÀ IoU — CÁCH GIẢI THÍCH TRƯỚC LỚP

**Nhãn chuẩn** là vùng hư hỏng tham chiếu do người gán nhãn vẽ trên ảnh theo quy tắc đã thống nhất, sau đó nên được người thứ hai kiểm tra. Với bài toán segmentation, nhãn thường là một mask hoặc polygon: pixel nằm trong vùng được đánh dấu là hư hỏng, pixel bên ngoài không thuộc vùng đó.

IoU so sánh vùng model khoanh với nhãn chuẩn:

`IoU = diện tích giao nhau / diện tích hợp của hai vùng`

- IoU gần `1,00`: hai vùng gần trùng nhau.
- IoU khoảng `0,50`: còn lệch đáng kể.
- IoU `0,95` không có nghĩa “95% khả năng gian lận”, cũng không phải độ chính xác chung của toàn hệ thống.

File `04_IOU_MINH_HOA_4_BUOC.png` có ví dụ tốt IoU `{high_iou:.3f}` và ví dụ lệch IoU `{low_iou:.3f}`.

**Lưu ý:** vùng xanh trong bộ này do script tạo để giảng giải khái niệm. Nó không phải ground truth đã được chuyên gia giám định xác nhận và không được dùng để công bố metric YOLO.
""")
    return label


def case_guide(case: dict) -> str:
    marker = "Ảnh có metadata khai báo AI/chỉnh sửa để kiểm tra provenance." if case["ai_marker"] else "Ảnh tổng hợp không có nhãn AI hiển thị trên pixel."
    return f"""# {case['title']}

## Nhập trên giao diện

1. Mở `http://127.0.0.1:8000/` và chọn **Nạp hồ sơ mới**.
2. Bật **Dùng hồ sơ mẫu** để backend tự cấp feature bảng; người demo không nhập JSON.
3. Nhập số tiền `{case['claim_amount']}`, ngày `{case['incident_date']}`, biển số `{case['plate']}`.
4. Nhập số điện thoại `{case['phone']}` và xưởng `{case['garage']}`.
5. Tải **Ảnh xe**: `{case['image_target']}`.
6. Tải **Chứng từ bồi thường**: `{case['document_target']}`.
7. Bấm **Phân tích hồ sơ** một lần và chờ Workbench tự mở.

## Bạn nên chỉ cho lớp xem

- **Mục đích:** {case['purpose']}
- **Kết quả mong đợi:** {case['expected']}
- **Nguồn gốc ảnh:** {marker}
- **Giới hạn:** vùng khoanh và cờ kiểm tra là gợi ý hỗ trợ người duyệt, không phải quyết định gian lận tự động.
"""


def build(output: Path, *, refresh: bool = False) -> Path:
    if output.exists() and not refresh:
        raise FileExistsError(f"Không ghi đè thư mục đã tồn tại: {output}")
    missing = [ASSET_ROOT / case["image"] for case in CASES if not (ASSET_ROOT / case["image"]).is_file()]
    if missing:
        raise FileNotFoundError("Thiếu ảnh nguồn:\n" + "\n".join(map(str, missing)))
    output.mkdir(parents=True, exist_ok=refresh)

    matrix = []
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
            f"Dùng hồ sơ mẫu: BẬT\nSố tiền: {case['claim_amount']}\nNgày sự cố: {case['incident_date']}\nBiển số: {case['plate']}\nSố điện thoại: {case['phone']}\nXưởng sửa chữa: {case['garage']}",
        )
        matrix.append({
            "STT": index,
            "Hồ sơ": case["folder"],
            "Tình huống": case["title"],
            "Giá trị trình diễn": case["purpose"],
            "Kết quả mong đợi": case["expected"],
        })

    label = build_iou_explainer(
        ASSET_ROOT / CASES[0]["image"], output / "00_GIAI_THICH_NHAN_CHUAN_VA_IOU", refresh=refresh
    )
    with (output / "01_MA_TRAN_3_HO_SO.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(matrix[0]))
        writer.writeheader()
        writer.writerows(matrix)

    prompts = {
        "mode": "generate",
        "tool": "OpenAI image generation",
        "assets": [
            {"file": CASES[0]["image"], "summary": "Dark red SUV, rear-left door and wheel-arch collision damage, Vietnamese apartment parking."},
            {"file": CASES[1]["image"], "summary": "Metallic blue sedan, right-side collision damage and broken mirror, Vietnamese repair garage."},
            {"file": CASES[2]["image"], "summary": "Silver pickup, front-left collision damage, wet Vietnamese urban roadside."},
        ],
        "notice": "All vehicle images are synthetic and intended only for classroom product demonstration.",
    }
    (output / "02_NGUON_GOC_DU_LIEU_TONG_HOP.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(ASSET_ROOT / "README.md", output / "03_PROMPT_TAO_ANH.md")
    write_text(output / "00_BAT_DAU_TU_DAY.md", """# BỘ DEMO LỚP HỌC MỚI — 3 HỒ SƠ

Toàn bộ ảnh, chứng từ, biển số, số điện thoại, xưởng và số tiền trong bộ này đều là dữ liệu tổng hợp. Không dùng làm bằng chứng thật.

## Thứ tự demo đề xuất

1. Mở `00_GIAI_THICH_NHAN_CHUAN_VA_IOU/04_IOU_MINH_HOA_4_BUOC.png` để giải thích nhãn chuẩn và IoU.
2. Mở sản phẩm tại `http://127.0.0.1:8000/`.
3. Chạy hồ sơ `01`: luồng đầy đủ với SUV đỏ.
4. Chạy hồ sơ `02`: sedan xanh dùng chung số điện thoại và xưởng với hồ sơ 01 để demo Quan hệ.
5. Chạy hồ sơ `03`: pickup bạc có metadata khai báo AI/chỉnh sửa để demo Nguồn gốc ảnh.
6. Trong mỗi hồ sơ, bật **Dùng hồ sơ mẫu**. Người dùng nghiệp vụ không phải nhập JSON.
7. Lưu một quyết định ở Workbench, rồi mở **Danh sách hồ sơ → Lịch sử** để chứng minh audit log.

Mỗi thư mục có `00_HUONG_DAN_TEST.md` và `01_THONG_TIN_NHAP.txt` riêng. Chạy theo thứ tự 01 → 02 → 03 để graph của case 02 có dữ liệu lịch sử.
""")

    inventory = []
    for path in sorted(
        item for item in output.rglob("*")
        if item.is_file() and item.name != "99_MANIFEST_SHA256.json"
    ):
        inventory.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "pack_version": "class-demo-fresh-v1",
        "case_count": len(CASES),
        "iou_explainer": label,
        "files": inventory,
    }
    (output / "99_MANIFEST_SHA256.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    parser.add_argument("--refresh", action="store_true", help="Ghi lại các file do script quản lý trong pack đã có.")
    args = parser.parse_args()
    built = build(args.output.resolve(), refresh=args.refresh)
    print(f"Demo pack: {built}")
    if args.make_zip:
        archive = Path(shutil.make_archive(str(built), "zip", root_dir=built.parent, base_dir=built.name))
        print(f"ZIP: {archive}")


if __name__ == "__main__":
    main()
