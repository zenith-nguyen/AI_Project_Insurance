"""Local-only research operations dashboard: streamlit run prototype/monitor_dashboard.py."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import streamlit as st


def read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("action") in {"STP", "SUPPLEMENT", "SIU"} and isinstance(event.get("duration_ms"), (int, float)):
            events.append(event)
    return events


st.set_page_config(page_title="Claim Review – giám sát nghiên cứu", layout="wide")
st.title("Giám sát luồng /verify")
st.caption("Thống kê từ log nghiên cứu. Không hiển thị claim_id hoặc dữ liệu cá nhân; không phải bằng chứng hiệu năng production.")
path = Path(os.getenv("INSURANCE_VERIFY_LOG", "runtime/audit/verify.jsonl"))
events = read_events(path)
if not events:
    st.info("Chưa có lượt /verify được ghi nhận ở đường dẫn cấu hình.")
else:
    modes = sorted({row.get("mode", "unknown") for row in events})
    mode = st.selectbox("Chế độ", modes)
    cohort = [row for row in events if row.get("mode") == mode]
    counts = Counter(row["action"] for row in cohort)
    n = len(cohort)
    durations = sorted(float(row["duration_ms"]) for row in cohort)
    p95 = durations[min(n - 1, int((n - 1) * .95 + .9999))]
    a, b, c, d = st.columns(4)
    a.metric("Lượt", n)
    b.metric("STP", f"{counts['STP'] / n:.1%}")
    c.metric("Bổ sung", f"{counts['SUPPLEMENT'] / n:.1%}")
    d.metric("SIU", f"{counts['SIU'] / n:.1%}")
    st.metric("Độ trễ p95 (ms)", f"{p95:.1f}")
    st.bar_chart({"Lượt": {action: counts[action] for action in ("STP", "SUPPLEMENT", "SIU")}})
    st.caption("Latency là thời gian /verify ở API, không phải thời gian xử lý bồi thường. Số liệu fixture chỉ là demo.")
