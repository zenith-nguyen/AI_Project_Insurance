"""Local claim intake and evidence storage for the research workbench."""
from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PIL import Image

from .schemas import ClaimIntakeRequest, ClaimIntakeRecord, EvidenceUploadRecord


CLAIM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"},
    "document": {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"},
}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


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
        claim_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "evidence_manifest.json").write_text("[]\n", encoding="utf-8")
        graph = {
            "scored_at": payload["scored_at"],
            "known_risky_claims": [],
            "nodes": [{"id": claim_id, "entity_type": "claim", "available_at": created_at}],
            "edges": [],
        }
        (root / "entities.json").write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        return ClaimIntakeRecord(claim_id=claim_id, created_at=created_at, status="stored")

    def save_evidence(self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes) -> EvidenceUploadRecord:
        root = self.claim_root(claim_id)
        if not (root / "claim.json").is_file():
            raise KeyError(claim_id)
        if kind not in ALLOWED_EXTENSIONS:
            raise ValueError("Evidence kind must be image or document.")
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
            "observed_at": observed_at,
        }
        manifest.append(item)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return EvidenceUploadRecord(claim_id=claim_id, **item)

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
