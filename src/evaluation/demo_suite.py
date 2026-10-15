"""Audit and normalize the externally supplied 27-case synthetic demo suite."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from PIL import Image
from pypdf import PdfReader


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_pack_root(path: Path) -> Path:
    """Accept either the outer extracted folder or the directory containing the manifest."""
    path = Path(path).resolve()
    if (path / "BAT_DAU_O_DAY.md").is_file():
        return path
    matches = [candidate.parent for candidate in path.rglob("BAT_DAU_O_DAY.md")]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one demo-suite root below {path}; found {len(matches)}")
    return matches[0]


def unique_paths(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value).replace("\\", "/") for value in values))


def _safe_relative(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes demo pack: {relative}")
    return target


def _render_first_page(source: Path, destination: Path, *, scale: float = 2.0) -> None:
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise RuntimeError("Install requirements-document.txt to render the demo PDFs") from error
    document = pdfium.PdfDocument(str(source))
    if len(document) != 1:
        raise ValueError(f"Expected a one-page quotation PDF: {source}")
    image = document[0].render(scale=scale).to_pil().convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)


def _pdf_text(path: Path) -> str:
    pages = PdfReader(str(path)).pages
    return "\n".join((page.extract_text() or "").strip() for page in pages).strip()


def audit_demo_suite(source: Path) -> dict[str, Any]:
    root = find_pack_root(source)
    input_root = root / "INPUT_GUI_BAN"
    expected_root = root / "KIEM_TRA_RIENG"
    run = json.loads((input_root / "run_manifest.json").read_text(encoding="utf-8-sig"))
    cases = list(run.get("cases", []))
    issues: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    claim_ids: set[str] = set()
    for item in cases:
        claim_path = _safe_relative(input_root, item["claim_file"])
        claim = json.loads(claim_path.read_text(encoding="utf-8-sig"))
        claim_id = str(claim["claim_id"])
        if claim_id in claim_ids:
            issues.append({"claim_id": claim_id, "code": "duplicate_claim_id"})
        claim_ids.add(claim_id)
        expected_path = expected_root / f"{claim_id}.json"
        if not expected_path.is_file():
            issues.append({"claim_id": claim_id, "code": "missing_expected_result"})
            continue
        expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
        documents = [str(value) for value in claim.get("document_files", [])]
        duplicate_count = len(documents) - len(unique_paths(documents))
        if duplicate_count:
            issues.append({"claim_id": claim_id, "code": "duplicate_document_path", "count": duplicate_count})
        for relative in unique_paths([*claim.get("image_files", []), *documents]):
            if not _safe_relative(input_root, relative).is_file():
                issues.append({"claim_id": claim_id, "code": "missing_asset", "path": relative})
        quote_pdf = claim_path.parent / "bao_gia.pdf"
        quote_png = claim_path.parent / "bao_gia.png"
        try:
            with Image.open(quote_png) as image:
                image.verify()
            quote_png_valid = True
        except Exception:
            quote_png_valid = False
            issues.append({"claim_id": claim_id, "code": "invalid_quote_png", "path": str(quote_png)})
        transcript = _pdf_text(quote_pdf)
        if not transcript:
            issues.append({"claim_id": claim_id, "code": "empty_quote_pdf_text"})
        related_path = claim_path.parent / "related_claims.json"
        if related_path.is_file():
            target_time = datetime.fromisoformat(str(claim["submitted_at"]).replace("Z", "+00:00"))
            related_rows = json.loads(related_path.read_text(encoding="utf-8-sig"))
            future_references = [
                str(row["claim_id"])
                for row in related_rows
                if row.get("claim_id") != claim_id
                and datetime.fromisoformat(str(row["submitted_at"]).replace("Z", "+00:00")) > target_time
            ]
            if future_references:
                issues.append({
                    "claim_id": claim_id,
                    "code": "point_in_time_oracle_uses_future_references",
                    "reference_claim_ids": future_references,
                })
        case_rows.append({
            "claim_id": claim_id,
            "scenario": expected.get("scenario"),
            "role": expected.get("role"),
            "mode": item.get("mode"),
            "expected_route": expected.get("expected_route"),
            "quote_png_valid": quote_png_valid,
            "quote_transcript_characters": len(transcript),
        })

    asset_manifest = json.loads((root / "asset_manifest.json").read_text(encoding="utf-8-sig"))
    missing_manifest_assets: list[str] = []
    hash_mismatches: list[str] = []
    for row in asset_manifest:
        target = _safe_relative(root, row["path"])
        if not target.is_file():
            missing_manifest_assets.append(row["path"])
        elif sha256_file(target) != row["sha256"]:
            hash_mismatches.append(row["path"])
    fatal_codes = {"duplicate_claim_id", "missing_expected_result", "missing_asset", "empty_quote_pdf_text"}
    return {
        "schema_version": "demo27_audit_v1",
        "source_schema_version": run.get("schema_version"),
        "source_root": str(root),
        "case_count": len(case_rows),
        "scenario_counts": dict(sorted(Counter(row["scenario"] for row in case_rows).items())),
        "role_counts": dict(sorted(Counter(row["role"] for row in case_rows).items())),
        "mode_counts": dict(sorted(Counter(row["mode"] for row in case_rows).items())),
        "asset_manifest_entries": len(asset_manifest),
        "asset_manifest_missing": missing_manifest_assets,
        "asset_manifest_hash_mismatch": hash_mismatches,
        "issues": issues,
        "fatal_issue_count": sum(item["code"] in fatal_codes for item in issues) + len(missing_manifest_assets) + len(hash_mismatches),
        "repairable_issue_count": sum(item["code"] in {"duplicate_document_path", "invalid_quote_png"} for item in issues),
        "semantic_limitation_count": sum(item["code"] == "point_in_time_oracle_uses_future_references" for item in issues),
        "cases": case_rows,
        "data_classification": {
            "synthetic": True,
            "contains_real_claim_ground_truth": False,
            "domain_accuracy_claim_allowed": False,
            "allowed_uses": ["engineering_demo", "workflow_uat", "synthetic_ocr_comparison", "graph_rule_tests"],
        },
    }


def prepare_demo_suite(source: Path, output: Path, *, overwrite: bool = False) -> dict[str, Any]:
    root = find_pack_root(source)
    input_root = root / "INPUT_GUI_BAN"
    expected_root = root / "KIEM_TRA_RIENG"
    audit = audit_demo_suite(root)
    if audit["fatal_issue_count"]:
        raise ValueError(f"Demo suite has {audit['fatal_issue_count']} fatal audit issue(s)")
    output = Path(output).resolve()
    if output.exists():
        if not overwrite:
            raise FileExistsError(output)
        shutil.rmtree(output)
    output.mkdir(parents=True)
    run = json.loads((input_root / "run_manifest.json").read_text(encoding="utf-8-sig"))

    vehicle_images = output / "assets" / "vehicle_images"
    vehicle_documents = output / "assets" / "vehicle_documents"
    shutil.copytree(input_root / "images", vehicle_images)
    shutil.copytree(input_root / "GIAY_TO_CHUNG", vehicle_documents)
    cases_output = output / "cases"
    expected_output = output / "expected_private"
    ocr_root = output / "ocr_benchmark"
    manifest_rows: list[dict[str, Any]] = []
    normalized_cases: list[dict[str, Any]] = []

    for item in run["cases"]:
        source_claim_path = _safe_relative(input_root, item["claim_file"])
        source_case = source_claim_path.parent
        claim = json.loads(source_claim_path.read_text(encoding="utf-8-sig"))
        claim_id = str(claim["claim_id"])
        destination_case = cases_output / claim_id
        destination_case.mkdir(parents=True)
        for name in ("to_khai.pdf", "bao_gia.pdf", "metadata.json", "fixture.json", "graph.json", "reference_claims.json", "related_claims.json"):
            source_file = source_case / name
            if source_file.is_file():
                shutil.copy2(source_file, destination_case / name)

        expected_path = expected_root / f"{claim_id}.json"
        expected_output.mkdir(exist_ok=True)
        shutil.copy2(expected_path, expected_output / expected_path.name)
        quote_image = ocr_root / "images" / f"{claim_id}.png"
        quote_transcript = ocr_root / "transcripts" / f"{claim_id}.txt"
        _render_first_page(source_case / "bao_gia.pdf", quote_image)
        quote_transcript.parent.mkdir(parents=True, exist_ok=True)
        quote_transcript.write_text(_pdf_text(source_case / "bao_gia.pdf") + "\n", encoding="utf-8")

        clean_documents = unique_paths(claim.get("document_files", []))
        shared_documents = [
            value.removeprefix("GIAY_TO_CHUNG/") for value in clean_documents if value.startswith("GIAY_TO_CHUNG/")
        ]
        normalized_claim = {
            **claim,
            "source_schema_version": claim.get("schema_version"),
            "schema_version": "demo_claim_normalized_v1",
            "data_origin": "synthetic_demo27_normalized",
            "image_files": [f"assets/vehicle_images/{Path(value).name}" for value in unique_paths(claim.get("image_files", []))],
            "document_files": [
                f"cases/{claim_id}/to_khai.pdf",
                f"ocr_benchmark/images/{claim_id}.png",
                *[f"assets/vehicle_documents/{value}" for value in shared_documents],
            ],
            "source_quote_pdf": f"cases/{claim_id}/bao_gia.pdf",
            "expected_result_file": f"expected_private/{claim_id}.json",
        }
        (destination_case / "claim.json").write_text(
            json.dumps(normalized_claim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
        submitted_at = datetime.fromisoformat(str(claim["submitted_at"]).replace("Z", "+00:00"))
        manifest_rows.append({
            "sample_id": f"DEMO27-{claim_id}",
            "split": "validation",
            "image_path": f"images/{claim_id}.png",
            "image_sha256": sha256_file(quote_image),
            "document_type": "repair_estimate",
            "reference_text_path": f"transcripts/{claim_id}.txt",
            "annotation_status": "source_verified",
            "consent_or_legal_basis": "synthetic_demo_pack_provided_by_project_team",
            "pii_treatment": "synthetic",
            "benchmark_tier": "synthetic_engineering",
            "reference_fields": {
                "total_vnd": str(expected.get("quotation_total_vnd", "")),
                "document_date": submitted_at.strftime("%d/%m/%Y"),
                "plate_number": str(expected.get("plate_in_documents", "")),
            },
            "scenario": expected.get("scenario"),
            "role": expected.get("role"),
        })
        normalized_cases.append({
            "claim_id": claim_id,
            "scenario": expected.get("scenario"),
            "role": expected.get("role"),
            "mode": item.get("mode"),
            "claim_file": f"cases/{claim_id}/claim.json",
            "expected_file": f"expected_private/{claim_id}.json",
            "vehicle_images": normalized_claim["image_files"],
            "minimal_documents": [f"ocr_benchmark/images/{claim_id}.png"],
            "full_documents": normalized_claim["document_files"],
        })

    (ocr_root / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest_rows), encoding="utf-8"
    )
    suite_manifest = {
        "schema_version": "demo27_normalized_v1",
        "source_schema_version": run.get("schema_version"),
        "case_count": len(normalized_cases),
        "reference_scope": "isolated_per_case",
        "data_classification": audit["data_classification"],
        "ocr_benchmark": {
            "tier": "synthetic_engineering",
            "manifest": "ocr_benchmark/manifest.jsonl",
            "page_count": len(manifest_rows),
            "domain_accuracy_claim_allowed": False,
        },
        "cases": normalized_cases,
    }
    (output / "suite_manifest.json").write_text(
        json.dumps(suite_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "source_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "00_README.md").write_text(
        "# Bộ 27 hồ sơ đã chuẩn hóa\n\n"
        "Bộ này chỉ dùng cho demo kỹ thuật, workflow UAT, rule/graph test và so sánh OCR tổng hợp. "
        "Không dùng để công bố độ chính xác trên hồ sơ bảo hiểm Việt Nam thật.\n\n"
        "- `suite_manifest.json`: danh mục 27 case và file dùng để nạp.\n"
        "- `expected_private/`: đáp án; không đưa vào input model.\n"
        "- `ocr_benchmark/`: 27 ảnh báo giá render lại từ PDF và transcript nguồn.\n"
        "- `source_audit.json`: lỗi nguồn và các sửa chữa đã kiểm toán.\n",
        encoding="utf-8",
    )
    inventory = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "integrity_manifest.json"):
        inventory.append({"path": path.relative_to(output).as_posix(), "size": path.stat().st_size, "sha256": sha256_file(path)})
    integrity = {"schema_version": "demo27_integrity_v1", "file_count": len(inventory), "files": inventory}
    (output / "integrity_manifest.json").write_text(
        json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {**suite_manifest, "output": str(output), "integrity_file_count": len(inventory), "source_audit": audit}


def validate_prepared_demo_suite(path: Path) -> dict[str, Any]:
    root = Path(path).resolve()
    suite_path = root / "suite_manifest.json"
    integrity_path = root / "integrity_manifest.json"
    if not suite_path.is_file() or not integrity_path.is_file():
        raise FileNotFoundError("suite_manifest.json and integrity_manifest.json are required")
    suite = json.loads(suite_path.read_text(encoding="utf-8-sig"))
    integrity = json.loads(integrity_path.read_text(encoding="utf-8-sig"))
    missing: list[str] = []
    mismatched: list[str] = []
    for row in integrity.get("files", []):
        target = _safe_relative(root, row["path"])
        if not target.is_file():
            missing.append(row["path"])
        elif target.stat().st_size != row["size"] or sha256_file(target) != row["sha256"]:
            mismatched.append(row["path"])
    case_ids = [row["claim_id"] for row in suite.get("cases", [])]
    case_path_errors: list[str] = []
    for row in suite.get("cases", []):
        for key in ("claim_file", "expected_file"):
            if not _safe_relative(root, row[key]).is_file():
                case_path_errors.append(f"{row['claim_id']}:{key}")
        for key in ("vehicle_images", "minimal_documents", "full_documents"):
            for relative in row.get(key, []):
                if not _safe_relative(root, relative).is_file():
                    case_path_errors.append(f"{row['claim_id']}:{key}:{relative}")
    passed = not missing and not mismatched and not case_path_errors and len(case_ids) == len(set(case_ids)) == suite.get("case_count")
    return {
        "schema_version": "demo27_validation_v1",
        "passed": passed,
        "case_count": len(case_ids),
        "integrity_files_checked": len(integrity.get("files", [])),
        "missing_files": missing,
        "hash_or_size_mismatches": mismatched,
        "case_path_errors": case_path_errors,
        "domain_accuracy_claim_allowed": bool(suite.get("data_classification", {}).get("domain_accuracy_claim_allowed", False)),
    }
