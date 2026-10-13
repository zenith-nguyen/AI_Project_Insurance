"""Layered media-authenticity checks with explicit uncertainty.

The module treats provenance and detector output as evidence. Absence of a
watermark or metadata is never interpreted as proof that an image is genuine.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from PIL import ExifTags, Image

from src.api.schemas import AuthenticityFinding, MediaAuthenticityReport


AI_MARKERS = {
    "trainedalgorithmicmedia": "IPTC digital source type says trained algorithmic media.",
    "compositewithtrainedalgorithmicmedia": "IPTC digital source type says the asset includes generative-AI content.",
    "adobe firefly": "Metadata names Adobe Firefly.",
    "midjourney": "Metadata names Midjourney.",
    "stable diffusion": "Metadata names Stable Diffusion.",
    "automatic1111": "Metadata names AUTOMATIC1111.",
    "comfyui": "Metadata names ComfyUI.",
    "dall-e": "Metadata names DALL-E.",
    "openai image": "Metadata names an OpenAI image generator.",
    "generative ai": "Metadata declares generative-AI use.",
    "ai generated": "Metadata declares AI-generated content.",
}


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)


class MediaAuthenticityAnalyzer:
    """Collect deterministic metadata and optional signed-provenance evidence."""

    version = "media_authenticity_v1"

    def __init__(
        self,
        *,
        exiftool: str | None = None,
        c2patool: str | None = None,
        c2pa_runner: Callable[[Path], dict[str, Any] | None] | None = None,
    ) -> None:
        self.exiftool = shutil.which("exiftool") if exiftool is None else (exiftool or None)
        self.c2patool = shutil.which("c2patool") if c2patool is None else (c2patool or None)
        self.c2pa_runner = c2pa_runner

    @staticmethod
    def _run_json(command: list[str]) -> Any:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"Command exited {completed.returncode}")
        return json.loads(completed.stdout)

    def _metadata(self, path: Path) -> tuple[dict[str, Any], list[AuthenticityFinding], dict[str, Any]]:
        findings: list[AuthenticityFinding] = []
        metadata: dict[str, Any] = {}
        image_info: dict[str, Any] = {}
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_info = {"format": image.format, "width": image.width, "height": image.height, "mode": image.mode}
            for tag_id, value in image.getexif().items():
                metadata[str(ExifTags.TAGS.get(tag_id, tag_id))] = str(value)
            for key in ("software", "comment", "description", "parameters", "prompt", "xmp"):
                if key in image.info:
                    metadata[key] = str(image.info[key])

        if self.exiftool:
            try:
                rows = self._run_json([self.exiftool, "-j", "-G", "-n", str(path)])
                if rows:
                    metadata.update({str(key): value for key, value in rows[0].items() if key != "SourceFile"})
                findings.append(AuthenticityFinding(
                    code="exiftool_completed", source="exiftool", outcome="completed", severity="info",
                    explanation="ExifTool metadata extraction completed.",
                ))
            except Exception as error:
                findings.append(AuthenticityFinding(
                    code="exiftool_error", source="exiftool", outcome="error", severity="review",
                    explanation=f"ExifTool could not complete: {type(error).__name__}.",
                ))
        else:
            findings.append(AuthenticityFinding(
                code="exiftool_unavailable", source="exiftool", outcome="unavailable", severity="info",
                explanation="ExifTool is not installed; built-in EXIF/XMP extraction was used.",
            ))

        metadata_text = _flatten(metadata).lower()
        matched = sorted({message for marker, message in AI_MARKERS.items() if marker in metadata_text})
        for index, message in enumerate(matched, start=1):
            findings.append(AuthenticityFinding(
                code=f"ai_metadata_marker_{index}", source="metadata", outcome="detected", severity="review",
                explanation=message, confidence=0.8,
            ))
        if not metadata:
            findings.append(AuthenticityFinding(
                code="metadata_absent", source="metadata", outcome="absent", severity="info",
                explanation="No readable EXIF/XMP metadata was found. Social platforms and re-encoding may remove metadata.",
            ))
        return metadata, findings, image_info

    def _c2pa(self, path: Path) -> tuple[dict[str, Any] | None, list[AuthenticityFinding]]:
        findings: list[AuthenticityFinding] = []
        try:
            report = self.c2pa_runner(path) if self.c2pa_runner else (
                self._run_json([self.c2patool, str(path)]) if self.c2patool else None
            )
        except Exception as error:
            return None, [AuthenticityFinding(
                code="c2pa_error", source="c2pa", outcome="error", severity="review",
                explanation=f"C2PA validation could not complete: {type(error).__name__}.",
            )]
        if report is None:
            return None, [AuthenticityFinding(
                code="c2pa_unavailable", source="c2pa", outcome="unavailable", severity="info",
                explanation="c2patool is not installed; signed Content Credentials were not validated.",
            )]

        flattened = _flatten(report).lower()
        has_manifest = any(token in flattened for token in ("active_manifest", "claim_generator", "assertions"))
        invalid = any(token in flattened for token in ("validation_status", "tampered", "mismatch")) and any(
            token in flattened for token in ("error", "invalid", "failure", "mismatch")
        )
        ai_marker = any(marker in flattened for marker in AI_MARKERS)
        if invalid:
            findings.append(AuthenticityFinding(
                code="c2pa_validation_problem", source="c2pa", outcome="detected", severity="high",
                explanation="Content Credentials are present but contain a validation problem.", confidence=0.95,
            ))
        elif has_manifest and ai_marker:
            findings.append(AuthenticityFinding(
                code="c2pa_ai_assertion_present", source="c2pa", outcome="detected", severity="high",
                explanation="Content Credentials contain a generative-AI assertion; inspect validation status, signer trust and actions.", confidence=0.95,
            ))
        elif has_manifest:
            findings.append(AuthenticityFinding(
                code="c2pa_manifest_present", source="c2pa", outcome="completed", severity="info",
                explanation="Content Credentials were found. Provenance is available for reviewer inspection.", confidence=0.95,
            ))
        else:
            findings.append(AuthenticityFinding(
                code="c2pa_manifest_absent", source="c2pa", outcome="absent", severity="info",
                explanation="No Content Credentials manifest was found; this does not prove the image is genuine.",
            ))
        return report, findings

    def analyze(self, path: str | Path, *, evidence_id: str | None = None) -> MediaAuthenticityReport:
        asset = Path(path)
        if not asset.is_file():
            raise FileNotFoundError(asset)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        metadata, findings, image_info = self._metadata(asset)
        c2pa, c2pa_findings = self._c2pa(asset)
        findings.extend(c2pa_findings)
        findings.append(AuthenticityFinding(
            code="synthid_provider_not_integrated", source="synthid", outcome="unavailable", severity="info",
            explanation="No local SynthID image detector API is configured. A provider result must be recorded separately.",
        ))
        findings.append(AuthenticityFinding(
            code="forensic_model_not_configured", source="forensic_model", outcome="unavailable", severity="info",
            explanation="No pixel-forensics model has been validated for insurance images yet.",
        ))

        high = [item for item in findings if item.severity == "high"]
        review = [item for item in findings if item.severity == "review" and item.outcome == "detected"]
        verdict = "ai_provenance_detected" if any(item.code == "c2pa_ai_assertion_present" for item in high) else (
            "provenance_problem" if high else ("review" if review else "inconclusive")
        )
        return MediaAuthenticityReport(
            evidence_id=evidence_id, analyzer_version=self.version, sha256=digest, verdict=verdict,
            human_review_required=verdict != "inconclusive", findings=findings,
            metadata=metadata, image_info=image_info, c2pa_manifest=c2pa,
            limitations=[
                "Missing metadata or watermark is not evidence that media is camera-original.",
                "Metadata can be removed or forged; signed provenance must be validated against a trust policy.",
                "This module supports triage and cannot by itself establish insurance fraud.",
            ],
        )
