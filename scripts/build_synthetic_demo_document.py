"""Create a visibly synthetic repair estimate for the team demo."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prototype/demo_assets/synthetic_repair_estimate.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    if not path.is_file():
        path = Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    return ImageFont.truetype(str(path), size)


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1100, 1450), "#fbfaf6")
    draw = ImageDraw.Draw(image)
    ink, muted, teal = "#183238", "#65797c", "#11786f"
    draw.rectangle((0, 0, 1100, 24), fill=teal)
    draw.text((72, 75), "DEMO REPAIR ESTIMATE", font=font(43, True), fill=ink)
    draw.text((74, 142), "SYNTHETIC DOCUMENT  •  NOT A REAL INVOICE", font=font(22, True), fill="#b34c3d")
    draw.line((72, 204, 1028, 204), fill="#bccbc8", width=3)
    lines = [
        ("Document", "EST-DEMO-001"),
        ("Claim ID", "CLM-DEMO-SYN-001"),
        ("Vehicle", "Unbranded silver sedan"),
        ("Plate", "51G-001.88 (synthetic)"),
        ("Incident date", "2015-02-28"),
        ("Issued", "2026-10-13 (demo)"),
    ]
    y = 255
    for label, value in lines:
        draw.text((78, y), label.upper(), font=font(20, True), fill=muted)
        draw.text((365, y - 4), value, font=font(27), fill=ink)
        y += 73
    draw.rectangle((72, 742, 1028, 808), fill="#e7f0ee")
    draw.text((90, 759), "WORK ITEM", font=font(21, True), fill=ink)
    draw.text((794, 759), "DEMO UNITS", font=font(21, True), fill=ink)
    items = [("Front bumper replacement", "25,000"), ("Front-left fender repair", "22,000"), ("Paint and inspection", "14,620")]
    y = 845
    for label, amount in items:
        draw.text((90, y), label, font=font(26), fill=ink)
        draw.text((830, y), amount, font=font(26), fill=ink)
        draw.line((90, y + 54, 1010, y + 54), fill="#d9e1df", width=2)
        y += 104
    draw.text((638, 1195), "ESTIMATED TOTAL", font=font(21, True), fill=muted)
    draw.text((785, 1240), "61,620", font=font(42, True), fill=teal)
    draw.text((72, 1360), "For product demonstration only. All identities, amounts and evidence are synthetic.", font=font(16), fill=muted)
    image.save(OUTPUT, optimize=True)
    return OUTPUT


if __name__ == "__main__":
    print(build())
