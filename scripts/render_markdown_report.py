from __future__ import annotations

import argparse
import re
from pathlib import Path

import markdown


STYLE = """
:root{--ink:#172326;--muted:#647579;--line:#d9e1e0;--navy:#142d33;--teal:#17877f;--paper:#f5f7f7;--warn:#fff4df}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.62 "Segoe UI",Arial,sans-serif}
header{background:var(--navy);color:white;padding:34px max(28px,calc((100vw - 1100px)/2))}header b{font-size:14px;letter-spacing:.11em;color:#8fd0c7}header h1{margin:7px 0 0;font-size:34px}
main{max-width:1100px;margin:28px auto;background:white;border:1px solid var(--line);padding:42px 52px}main img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;margin:14px 0 24px}h1{font-size:32px}h2{font-size:23px;margin-top:38px;padding-top:8px;border-top:2px solid var(--navy)}h3{font-size:18px;margin-top:28px;color:#174f52}p,li{max-width:92ch}table{width:100%;border-collapse:collapse;margin:18px 0 25px;font-size:14px}th,td{padding:11px 12px;border:1px solid var(--line);vertical-align:top}th{background:#eaf2f1;text-align:left}blockquote{margin:18px 0;padding:14px 18px;border-left:4px solid var(--teal);background:#eff8f6}code{background:#eef2f1;padding:2px 5px;border-radius:3px}strong{color:#102f32}a{color:#08756e}.footer{max-width:1100px;margin:0 auto 30px;color:var(--muted);font-size:12px}@media print{body{background:white}header{padding:20px 0;color:#172326;background:white;border-bottom:3px solid #142d33}main{border:0;margin:0 auto;padding:25px 0}h2{break-after:avoid}table{break-inside:avoid}p:has(> img){break-before:page;break-after:page;min-height:700px;display:flex;align-items:center}main img{break-inside:avoid;width:100%;margin:0}.footer{display:none}}@media(max-width:760px){main{margin:0;padding:24px 18px;border:0}header{padding:25px 18px}table{font-size:12px;display:block;overflow:auto}}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    match = re.search(r"\*\*(?:Ngày cập nhật|Cập nhật):\*\*\s*(\d{1,2}/\d{1,2}/\d{4})", source)
    report_date = match.group(1) if match else "TÀI LIỆU DỰ ÁN"
    body = markdown.markdown(source, extensions=["tables", "fenced_code", "sane_lists"])
    html = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{args.title}</title><style>{STYLE}</style></head><body><header><b>AI PROJECT INSURANCE · {report_date}</b><h1>{args.title}</h1></header><main>{body}</main><div class="footer">Bản trình bày được tạo từ tài liệu nguồn trong repository; số liệu nghiên cứu không phải cam kết production.</div></body></html>"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
