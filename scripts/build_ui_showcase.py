"""Build one offline HTML showcase from the three current localhost screenshots."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def image_data(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def build(screenshot_dir: Path, output: Path) -> Path:
    images = {
        "DASHBOARD_IMAGE": image_data(screenshot_dir / "dashboard.png"),
        "INTAKE_IMAGE": image_data(screenshot_dir / "intake.png"),
        "WORKBENCH_IMAGE": image_data(screenshot_dir / "workbench.png"),
    }
    html = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claim Review · UI hiện hành</title>
<style>
:root{--ink:#102f35;--teal:#0d746c;--dark:#0d3338;--paper:#f3f7f6;--line:#cadbd8}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}.top{background:var(--dark);color:white;padding:24px 5vw;display:flex;gap:20px;align-items:center;justify-content:space-between}.top h1{margin:0;font-size:26px}.top p{margin:5px 0 0;color:#b7d7d3}.live{display:flex;gap:8px;flex-wrap:wrap}.live a,.tabs button{border:1px solid #74aaa5;background:white;color:var(--teal);padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:700;cursor:pointer}.wrap{max-width:1500px;margin:24px auto;padding:0 22px}.notice{background:#e9f4f2;border:1px solid var(--line);padding:16px 18px;border-radius:10px;margin-bottom:18px}.tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}.tabs button.active{background:var(--teal);color:white}.panel{display:none;background:white;border:1px solid var(--line);padding:14px;border-radius:12px;box-shadow:0 8px 30px #15383b10}.panel.active{display:block}.panel h2{margin:3px 0 12px}.panel img{width:100%;height:auto;display:block;border:1px solid #dce7e5}.caption{color:#557074;margin:10px 2px 0}.foot{padding:20px;text-align:center;color:#617679}@media(max-width:800px){.top{display:block}.live{margin-top:15px}}
</style></head><body>
<header class="top"><div><h1>Claim Review · UI hiện hành</h1><p>Ảnh chụp từ localhost ngày 20/10/2026 · cùng giao diện với code trong Git</p></div><nav class="live"><a href="http://127.0.0.1:8000/?view=dashboard">Mở Dashboard live</a><a href="http://127.0.0.1:8000/?view=intake">Mở Nạp hồ sơ live</a><a href="http://127.0.0.1:8000/?view=workbench&claim_id=CLM-2026-00418">Mở Workbench live</a><a href="http://127.0.0.1:8000/docs">API docs</a></nav></header>
<main class="wrap"><div class="notice"><b>Cách dùng:</b> file này xem được offline để biết tổng quan UI. Muốn thao tác thật, chạy <code>python scripts/handoff.py up</code> (macOS: <code>python3</code>) rồi bấm các nút “live”. Dữ liệu trên ảnh là fixture demo; số liệu live thay đổi theo hồ sơ.</div>
<div class="tabs"><button class="active" data-tab="dashboard">1 · Dashboard</button><button data-tab="intake">2 · Nạp hồ sơ</button><button data-tab="workbench">3 · Workbench</button></div>
<section id="dashboard" class="panel active"><h2>Dashboard · hàng đợi, lịch sử, vận hành và model proof</h2><img alt="Dashboard Claim Review hiện hành" src="DASHBOARD_IMAGE"><p class="caption">Quản lý hồ sơ theo mức ưu tiên; xem job, chính sách chứng từ, roadmap và bằng chứng model local.</p></section>
<section id="intake" class="panel"><h2>Nạp hồ sơ · người dùng chỉ tải ảnh/chứng từ</h2><img alt="Màn hình nạp hồ sơ hiện hành" src="INTAKE_IMAGE"><p class="caption">Không yêu cầu người dùng nghiệp vụ nhập JSON; thông tin kỹ thuật do backend tích hợp sau.</p></section>
<section id="workbench" class="panel"><h2>Workbench · giải thích và quyết định của con người</h2><img alt="Workbench Claim Review hiện hành" src="WORKBENCH_IMAGE"><p class="caption">Kết hợp điểm hàng đợi, loại đầu vào, cờ kiểm tra, business explanation, bằng chứng và audit.</p></section></main>
<footer class="foot">Technical PoC · AI hỗ trợ rà soát, không tự kết luận gian lận hoặc tự từ chối bồi thường.</footer>
<script>const buttons=[...document.querySelectorAll('[data-tab]')],panels=[...document.querySelectorAll('.panel')];buttons.forEach(b=>b.onclick=()=>{buttons.forEach(x=>x.classList.toggle('active',x===b));panels.forEach(p=>p.classList.toggle('active',p.id===b.dataset.tab))})</script></body></html>"""
    for marker, value in images.items():
        html = html.replace(marker, value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshot-dir", type=Path, default=ROOT / "runtime/ui_showcase")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/final_handoff/04_UI_HTML_MAU.html")
    args = parser.parse_args()
    print(build(args.screenshot_dir, args.output))


if __name__ == "__main__":
    main()
