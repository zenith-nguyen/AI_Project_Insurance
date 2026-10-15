"""Render the evidence-backed model roadmap for reports and handoff."""
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "configs/model_improvement_status.v1.yaml"
OUTPUT = ROOT / "reports/MODEL_IMPROVEMENT_STATUS_2026-10-15.md"
STATUS = {
    "complete_engineering": "Đã xong phần kỹ thuật",
    "in_progress": "Đang triển khai/đánh giá",
    "waiting_for_domain_data": "Chờ dữ liệu đúng miền",
}


def render(source: Path = SOURCE, output: Path = OUTPUT) -> str:
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    milestones = sorted(payload["milestones"].values(), key=lambda item: item["order"])
    lines = [
        "# Trạng thái nâng cấp model và giá trị nghiệp vụ",
        "",
        f"Cập nhật: {payload['updated_at']}. Mục tiêu phát hành: `{payload['release_target']}`.",
        "",
        payload["summary"]["message"],
        "",
        "> Quy ước: “Đã xong phần kỹ thuật” chỉ xác nhận pipeline/safeguard đã có kiểm thử. Production readiness còn cần validation đúng miền, security và UAT.",
        "",
        "| # | Hạng mục | Trạng thái | Bằng chứng/metric hiện tại | Giá trị nghiệp vụ | Đang thiếu |",
        "|---:|---|---|---|---|---|",
    ]
    for item in milestones:
        clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item['order']} | {clean(item['title'])} | {STATUS.get(item['status'], item['status'])} | "
            f"{clean(item['current_metric'])} | {clean(item['business_value'])} | {clean(item['blocked_by'])} |"
        )
    lines += ["", "## Chi tiết gate và việc tiếp theo", ""]
    for item in milestones:
        lines += [
            f"### {item['order']:02d}. {item['title']}", "",
            f"- **Bằng chứng kỹ thuật:** {item['technical_evidence']}",
            f"- **KPI nghiệp vụ:** {item['business_kpi']}",
            f"- **Điều kiện đạt:** {item['gate']}",
            f"- **Việc tiếp theo:** {item['next_action']}", "",
        ]
    rendered = "\n".join(lines).rstrip() + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return rendered


if __name__ == "__main__":
    print(render())
