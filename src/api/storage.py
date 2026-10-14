"""Local claim intake and evidence storage for the research workbench."""
from __future__ import annotations

import hashlib
import io
import json
import re
import secrets
from datetime import datetime, timezone
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageStat

from .schemas import CaptureSessionRecord, ClaimAnalysis, ClaimIntakeRequest, ClaimIntakeRecord, EvidenceUploadRecord


CLAIM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"},
    "document": {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"},
}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
CAPTURE_TTL_MINUTES = 10
CAPTURE_ANGLE_PROMPTS = [
    "Chụp toàn cảnh xe từ góc trước bên trái.",
    "Chụp toàn cảnh xe từ góc sau bên phải.",
    "Chụp cận cảnh vùng hư hỏng và giữ một phần biển số trong khung hình.",
    "Chụp vùng hư hỏng từ góc thấp hơn tay nắm cửa.",
]


def _valid_signature(extension: str, content: bytes) -> bool:
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".tif", ".tiff"}:
        return content.startswith((b"II*\x00", b"MM\x00*"))
    if extension == ".webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


def validate_claim_id(claim_id: str) -> str:
    if not CLAIM_ID.fullmatch(claim_id):
        raise ValueError("claim_id must contain 3-64 letters, numbers, hyphens or underscores.")
    return claim_id


def _image_fingerprints(content: bytes) -> tuple[str, list[int]]:
    """Small robust fingerprint for reuse search; it is not an AI detector."""
    with Image.open(io.BytesIO(content)) as image:
        rgb = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
        color_signature = [round(value) for value in ImageStat.Stat(rgb).mean]
        gray = rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.get_flattened_data())
    bits = []
    for row in range(8):
        start = row * 9
        bits.extend(pixels[start + column] > pixels[start + column + 1] for column in range(8))
    value = sum(int(bit) << index for index, bit in enumerate(bits))
    return f"{value:016x}", color_signature


def _hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


class RuntimeClaimStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def claim_root(self, claim_id: str) -> Path:
        return self.root / validate_claim_id(claim_id)

    def create(self, claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
        root = self.claim_root(claim_id)
        claim_file = root / "claim.json"
        if claim_file.exists():
            raise FileExistsError(claim_id)
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": "1.0",
            "claim_id": claim_id,
            "data_origin": "runtime_intake",
            "created_at": created_at,
            "scored_at": request.scored_at or created_at,
            "claim_amount": request.claim_amount,
            "incident_date": request.incident_date,
            "plate_number": request.plate_number,
            "tabular_features": request.tabular_features,
            "required_evidence": request.required_evidence,
        }
        root.mkdir(parents=True, exist_ok=False)
        (root / "documents").mkdir()
        (root / "vehicle_images").mkdir()
        (root / "authenticity").mkdir()
        (root / "capture_sessions").mkdir()
        claim_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "evidence_manifest.json").write_text("[]\n", encoding="utf-8")
        graph = {
            "data_status": "not_provided",
            "scored_at": payload["scored_at"],
            "known_risky_claims": [],
            "nodes": [{"id": claim_id, "entity_type": "claim", "available_at": created_at}],
            "edges": [],
        }
        (root / "entities.json").write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        return ClaimIntakeRecord(claim_id=claim_id, created_at=created_at, status="stored")

    def create_capture_session(self, claim_id: str) -> CaptureSessionRecord:
        root = self.claim_root(claim_id)
        if not (root / "claim.json").is_file():
            raise KeyError(claim_id)
        created = datetime.now(timezone.utc)
        random_prompt = secrets.choice(CAPTURE_ANGLE_PROMPTS)
        session_id = f"CAP-{secrets.token_hex(8)}"
        payload = {
            "claim_id": claim_id,
            "session_id": session_id,
            "created_at": created.isoformat(),
            "expires_at": (created + timedelta(minutes=CAPTURE_TTL_MINUTES)).isoformat(),
            "status": "issued",
            "instructions": [
                {"step": 1, "instruction": "Chụp toàn cảnh xe và bối cảnh xung quanh."},
                {"step": 2, "instruction": random_prompt},
                {"step": 3, "instruction": "Chụp cận cảnh vùng hư hỏng từ một góc khác bước 2."},
            ],
            "submissions": {},
            "assurance_level": "guided_unverified",
        }
        (root / "capture_sessions").mkdir(exist_ok=True)
        target = root / "capture_sessions" / f"{session_id}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return CaptureSessionRecord.model_validate(payload)

    def _capture_session(self, claim_id: str, session_id: str) -> tuple[Path, dict]:
        if not re.fullmatch(r"CAP-[0-9a-f]{16}", session_id):
            raise ValueError("Invalid capture session id.")
        path = self.claim_root(claim_id) / "capture_sessions" / f"{session_id}.json"
        if not path.is_file():
            raise KeyError(session_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if datetime.now(timezone.utc) > datetime.fromisoformat(payload["expires_at"]):
            payload["status"] = "expired"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raise ValueError("Capture session has expired.")
        return path, payload

    def save_evidence(
        self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes,
        capture_session_id: str | None = None, challenge_step: int | None = None,
    ) -> EvidenceUploadRecord:
        root = self.claim_root(claim_id)
        if not (root / "claim.json").is_file():
            raise KeyError(claim_id)
        if kind not in ALLOWED_EXTENSIONS:
            raise ValueError("Evidence kind must be image or document.")
        capture_path = None
        capture_payload = None
        if capture_session_id is not None:
            if kind != "image" or challenge_step is None:
                raise ValueError("Guided capture requires an image and challenge_step.")
            capture_path, capture_payload = self._capture_session(claim_id, capture_session_id)
            valid_steps = {int(item["step"]) for item in capture_payload["instructions"]}
            if challenge_step not in valid_steps:
                raise ValueError("challenge_step is not part of this capture session.")
            if str(challenge_step) in capture_payload.get("submissions", {}):
                raise ValueError("This capture step already has an uploaded image.")
        safe_name = Path(filename or "upload").name
        extension = Path(safe_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS[kind]:
            raise ValueError(f"Unsupported {kind} extension: {extension or '<none>'}")
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Evidence file must be between 1 byte and 15 MB.")
        if not _valid_signature(extension, content):
            raise ValueError("File content does not match its allowed extension.")
        if extension != ".pdf":
            try:
                with Image.open(io.BytesIO(content)) as image:
                    image.verify()
            except Exception as error:
                raise ValueError("Uploaded image cannot be decoded safely.") from error
        digest = hashlib.sha256(content).hexdigest()
        perceptual_hash, color_signature = _image_fingerprints(content) if kind == "image" else (None, None)
        evidence_id = f"EV-{uuid4().hex[:12]}"
        folder = root / ("vehicle_images" if kind == "image" else "documents")
        stored_name = f"{evidence_id}{extension}"
        (folder / stored_name).write_bytes(content)
        manifest_path = root / "evidence_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        observed_at = datetime.now(timezone.utc).isoformat()
        item = {
            "evidence_id": evidence_id,
            "kind": kind,
            "original_filename": safe_name,
            "stored_uri": f"runtime://claims/{claim_id}/{folder.name}/{stored_name}",
            "content_type": content_type,
            "size_bytes": len(content),
            "sha256": digest,
            "perceptual_hash": perceptual_hash,
            "color_signature": color_signature,
            "capture_session_id": capture_session_id,
            "challenge_step": challenge_step,
            "capture_assurance": "guided_unverified" if capture_session_id else None,
            "observed_at": observed_at,
        }
        manifest.append(item)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Any cached analysis predates this evidence and must not be served as current.
        (root / "analysis.json").unlink(missing_ok=True)
        if capture_path is not None and capture_payload is not None:
            capture_payload.setdefault("submissions", {})[str(challenge_step)] = evidence_id
            if len(capture_payload["submissions"]) == len(capture_payload["instructions"]):
                capture_payload["status"] = "completed"
            capture_path.write_text(json.dumps(capture_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return EvidenceUploadRecord(claim_id=claim_id, **item)

    def find_image_reuse(self, claim_id: str, evidence_id: str, *, max_distance: int = 4) -> list[dict]:
        """Find exact and visually similar runtime images from other claims."""
        own_manifest = json.loads((self.claim_root(claim_id) / "evidence_manifest.json").read_text(encoding="utf-8"))
        target = next((row for row in own_manifest if row.get("evidence_id") == evidence_id), None)
        if target is None or target.get("kind") != "image":
            return []
        matches = []
        for manifest_path in self.root.glob("*/evidence_manifest.json"):
            other_claim = manifest_path.parent.name
            if other_claim == claim_id:
                continue
            for row in json.loads(manifest_path.read_text(encoding="utf-8")):
                if row.get("kind") != "image":
                    continue
                exact = row.get("sha256") == target.get("sha256")
                distance = None
                if target.get("perceptual_hash") and row.get("perceptual_hash"):
                    distance = _hamming(target["perceptual_hash"], row["perceptual_hash"])
                target_color, row_color = target.get("color_signature"), row.get("color_signature")
                color_distance = None
                if target_color and row_color:
                    color_distance = sum((int(left) - int(right)) ** 2 for left, right in zip(target_color, row_color)) ** 0.5
                perceptual_match = distance is not None and distance <= max_distance and color_distance is not None and color_distance <= 60
                if exact or perceptual_match:
                    matches.append({
                        "claim_id": other_claim,
                        "evidence_id": row.get("evidence_id"),
                        "match_type": "exact" if exact else "perceptual",
                        "hamming_distance": distance,
                        "color_distance": round(color_distance, 3) if color_distance is not None else None,
                    })
        return sorted(matches, key=lambda item: (item["match_type"] != "exact", item.get("hamming_distance") or 0))

    def evidence_path(self, claim_id: str, evidence_id: str) -> Path:
        root = self.claim_root(claim_id)
        manifest_path = root / "evidence_manifest.json"
        if not manifest_path.is_file():
            raise KeyError(evidence_id)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = next((row for row in manifest if row.get("evidence_id") == evidence_id), None)
        if item is None:
            raise KeyError(evidence_id)
        relative = item["stored_uri"].removeprefix(f"runtime://claims/{claim_id}/")
        resolved = (root / relative).resolve()
        if root.resolve() not in resolved.parents or not resolved.is_file():
            raise ValueError("Stored evidence path is invalid.")
        return resolved

    def save_authenticity(self, claim_id: str, evidence_id: str, report: dict) -> None:
        root = self.claim_root(claim_id)
        self.evidence_path(claim_id, evidence_id)
        target = root / "authenticity" / f"{evidence_id}.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def load_authenticity(self, claim_id: str, evidence_id: str) -> dict | None:
        target = self.claim_root(claim_id) / "authenticity" / f"{evidence_id}.json"
        return json.loads(target.read_text(encoding="utf-8")) if target.is_file() else None

    def save_analysis(self, analysis: ClaimAnalysis) -> None:
        """Persist the latest analysis so a browser refresh or API restart is cheap."""
        root = self.claim_root(analysis.claim_id)
        # Golden fixtures live in the repository and are intentionally read-only.
        if not (root / "claim.json").is_file():
            return
        target = root / "analysis.json"
        target.write_text(analysis.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def load_analysis(self, claim_id: str) -> ClaimAnalysis | None:
        target = self.claim_root(claim_id) / "analysis.json"
        if not target.is_file():
            return None
        # utf-8-sig also accepts normal UTF-8 and tolerates files copied from
        # PowerShell versions that prepend a BOM.
        return ClaimAnalysis.model_validate_json(target.read_text(encoding="utf-8-sig"))
