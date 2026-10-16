"""Versioned governance registry for Vietnamese claim-document handling.

The registry tracks when product rules were reviewed and which official source
must be checked.  It never silently converts a web page change into an
insurance decision; a named reviewer must approve rule updates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


def _date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


@dataclass(frozen=True)
class DocumentPolicyRegistry:
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "DocumentPolicyRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        required = {"schema_version", "jurisdiction", "governance", "official_sources", "document_types"}
        missing = required - set(payload or {})
        if missing:
            raise ValueError(f"Document policy registry is missing: {sorted(missing)}")
        if payload["jurisdiction"] != "VN":
            raise ValueError("This release only supports the VN document-policy registry.")
        return cls(payload)

    def _state(self, policy: dict[str, Any], as_of: date) -> tuple[str, str]:
        valid_from = _date(policy.get("valid_from"))
        valid_to = _date(policy.get("valid_to"))
        next_review = _date(policy.get("next_review_due"))
        if valid_from and as_of < valid_from:
            return "future", "Quy tắc chưa đến ngày áp dụng."
        if valid_to and as_of > valid_to:
            return "expired", "Quy tắc đã hết thời hạn; không dùng để tự động xử lý."
        if next_review and as_of > next_review:
            return "review_due", "Đã đến hạn kiểm tra lại nguồn chính thức."
        if not policy.get("official_source_ids"):
            return "unverified", "Chưa gắn nguồn chính thức."
        return "current_reviewed", "Đã được rà soát trong chu kỳ hiện tại; vẫn cần người nghiệp vụ xác nhận."

    def public_summary(self, *, as_of: date | None = None) -> dict[str, Any]:
        today = as_of or date.today()
        aliases: dict[str, str] = {}
        rows: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        for policy_id, value in self.payload["document_types"].items():
            policy = dict(value)
            state, state_explanation = self._state(policy, today)
            counts[state] = counts.get(state, 0) + 1
            for alias in {policy_id, *policy.get("aliases", [])}:
                aliases[str(alias)] = policy_id
            rows.append({
                "policy_id": policy_id,
                "display_name": policy["display_name"],
                "aliases": policy.get("aliases", []),
                "required_business_fields": policy.get("required_business_fields", []),
                "valid_from": policy.get("valid_from"),
                "valid_to": policy.get("valid_to"),
                "last_verified_at": policy.get("last_verified_at"),
                "next_review_due": policy.get("next_review_due"),
                "official_source_ids": policy.get("official_source_ids", []),
                "automation_limit": policy.get("automation_limit"),
                "state": state,
                "state_explanation": state_explanation,
            })
        return {
            "schema_version": self.payload["schema_version"],
            "jurisdiction": self.payload["jurisdiction"],
            "as_of": today.isoformat(),
            "governance": self.payload["governance"],
            "official_sources": self.payload["official_sources"],
            "counts": counts,
            "aliases": aliases,
            "document_types": rows,
            "automatic_legal_updates": False,
            "update_rule": "Nguồn chính thức được giám sát; mọi thay đổi rule/schema phải có người nghiệp vụ duyệt và tạo version mới.",
        }
