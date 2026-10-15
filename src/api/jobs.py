"""In-process background jobs for long local model inference."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from uuid import uuid4

from .schemas import AnalysisJobRecord, AnalyzeRequest


STAGE_MESSAGES = {
    "queued": "Đang xếp hàng chờ tài nguyên suy luận.",
    "preparing": "Đang kiểm tra hồ sơ và kết quả có thể dùng lại.",
    "tabular": "Đang xếp hạng hồ sơ bằng dữ liệu khai báo.",
    "evidence": "Đang kiểm tra ảnh, hư hỏng và chứng từ.",
    "image_authenticity": "Đang kiểm tra metadata, provenance và ảnh dùng lại.",
    "damage": "YOLO đang khoanh vùng hư hỏng trên ảnh xe.",
    "document_loading": "Đang chuẩn bị các model đọc chứng từ.",
    "document_classifier": "DiT đang nhận dạng loại chứng từ.",
    "document_ocr": "PaddleOCR đang đọc chữ trên chứng từ.",
    "document_kie": "LayoutLMv3 đang trích xuất các trường cần đối chiếu.",
    "relationships": "Đang đối chiếu thông tin với hồ sơ trước đó.",
    "finalizing": "Đang tổng hợp bằng chứng và hướng xử lý.",
    "completed": "Đã hoàn tất; kết quả sẵn sàng mở.",
    "failed": "Phân tích gặp lỗi; hồ sơ và tệp đã tải vẫn được giữ.",
}


class AnalysisJobManager:
    """Serialize heavyweight models while keeping HTTP/UI responsive."""

    def __init__(self, service) -> None:
        self.service = service
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="claim-analysis")
        self._lock = Lock()
        self._jobs: dict[str, dict] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def start(self, claim_id: str, request: AnalyzeRequest) -> AnalysisJobRecord:
        with self._lock:
            for job in reversed(list(self._jobs.values())):
                if job["claim_id"] == claim_id and job["status"] in {"queued", "running"}:
                    return self._record(job)
            existing = self.service.get_analysis(claim_id)
            cache_hit = existing is not None and not request.force_recompute and not any([
                request.claim_amount is not None, request.incident_date, request.plate_number, request.evidence_ids,
            ])
            job_id = uuid4().hex
            job = {
                "job_id": job_id, "claim_id": claim_id, "status": "queued", "stage": "queued",
                "message": STAGE_MESSAGES["queued"], "created_at": self._now(), "started_at": None,
                "finished_at": None, "elapsed_seconds": 0.0, "result_available": False,
                "current_stage_elapsed_seconds": 0.0, "stage_durations_seconds": {},
                "cache_hit": cache_hit, "error": None, "_started_mono": None,
                "_created_mono": monotonic(), "_stage_started_mono": None,
            }
            self._jobs[job_id] = job
            self._executor.submit(self._run, job_id, request)
            return self._record(job)

    def _progress(self, job_id: str, stage: str, message: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            now = monotonic()
            self._close_stage(job, now)
            job["stage"] = stage
            job["message"] = message or STAGE_MESSAGES.get(stage, stage)
            job["_stage_started_mono"] = now
            job["current_stage_elapsed_seconds"] = 0.0
            if job["_started_mono"] is not None:
                job["elapsed_seconds"] = round(now - job["_started_mono"], 1)

    @staticmethod
    def _close_stage(job: dict, now: float) -> None:
        stage_started = job.get("_stage_started_mono")
        stage = job.get("stage")
        if stage_started is None or stage in {"completed", "failed"}:
            return
        elapsed = max(0.0, now - stage_started)
        durations = job["stage_durations_seconds"]
        durations[stage] = round(float(durations.get(stage, 0.0)) + elapsed, 1)
        job["current_stage_elapsed_seconds"] = 0.0
        job["_stage_started_mono"] = None

    def _run(self, job_id: str, request: AnalyzeRequest) -> None:
        with self._lock:
            job = self._jobs[job_id]
            now = monotonic()
            job.update(status="running", stage="preparing", message=STAGE_MESSAGES["preparing"], started_at=self._now())
            job["stage_durations_seconds"]["queued"] = round(now - job["_created_mono"], 1)
            job["_started_mono"] = now
            job["_stage_started_mono"] = now
            claim_id = job["claim_id"]
        try:
            self.service.analyze(claim_id, request, progress=lambda stage, message=None: self._progress(job_id, stage, message))
            with self._lock:
                job = self._jobs[job_id]
                now = monotonic()
                self._close_stage(job, now)
                job.update(status="completed", stage="completed", message=STAGE_MESSAGES["completed"],
                           finished_at=self._now(), result_available=True)
                job["elapsed_seconds"] = round(now - job["_started_mono"], 1)
        except Exception as error:  # job endpoint reports this safely; server keeps running
            with self._lock:
                job = self._jobs[job_id]
                now = monotonic()
                self._close_stage(job, now)
                job.update(status="failed", stage="failed", message=STAGE_MESSAGES["failed"],
                           finished_at=self._now(), error=f"{type(error).__name__}: {error}")
                job["elapsed_seconds"] = round(now - job["_started_mono"], 1)

    def get(self, job_id: str) -> AnalysisJobRecord | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job["status"] in {"queued", "running"} and job["_started_mono"] is not None:
                now = monotonic()
                job["elapsed_seconds"] = round(now - job["_started_mono"], 1)
                if job["_stage_started_mono"] is not None:
                    job["current_stage_elapsed_seconds"] = round(now - job["_stage_started_mono"], 1)
            return self._record(job)

    def list(self) -> list[AnalysisJobRecord]:
        with self._lock:
            return [self._record(job) for job in reversed(list(self._jobs.values()))]

    @staticmethod
    def _record(job: dict) -> AnalysisJobRecord:
        return AnalysisJobRecord.model_validate({key: value for key, value in job.items() if not key.startswith("_")})
