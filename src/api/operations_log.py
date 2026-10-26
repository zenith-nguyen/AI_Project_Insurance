"""Minimal JSONL verification telemetry with no raw model inputs or PII fields."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from .schemas import VerifyResponse


class VerificationLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = Lock()

    def append(self, result: VerifyResponse, duration_ms: float) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "claim_id": result.claim_id, "trace_id": result.trace_id,
            "mode": result.mode, "action": result.action,
            "analysis_status": result.analysis_status,
            "model_version": result.model_version,
            "duration_ms": round(duration_ms, 1),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
