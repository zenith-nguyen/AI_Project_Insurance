"""Build the numbered Markdown/PDF handoff pack and a checksum-protected ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import textwrap
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HANDBOOK = ROOT / "docs/handbook"
NUMBERED_DOCS = [HANDBOOK / f"{number:02d}_{name}.md" for number, name in enumerate([
    "START_HERE",
    "PRODUCT_AND_USER_FLOW",
    "INSTALLATION_AND_QUICKSTART",
    "API_AND_UI_INTEGRATION",
    "MODELS_METRICS_AND_LIMITATIONS",
    "DATA_ARTIFACTS_AND_GOVERNANCE",
    "OPERATIONS_AND_TROUBLESHOOTING",
    "RELEASE_SECURITY_AND_UAT",
    "DEFINITION_OF_DONE",
])]
SUPPORT_FILES = [
    ROOT / "contracts/claim_review_openapi.v1.json",
    ROOT / "prototype/api-client.js",
    ROOT / "configs/model_registry.v1.yaml",
    ROOT / "reports/PRODUCT_BUILD_STATUS_2026-10-13.md",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_lines(markdown: str, width: int = 102) -> list[str]:
    """Convert Markdown into stable printable lines without requiring a browser."""
    lines: list[str] = []
    in_code = False
    for raw in markdown.splitlines():
        stripped = raw.rstrip()
        if stripped.startswith("```"):
            in_code = not in_code
            lines.append("─" * 70)
            continue
        if in_code:
            lines.extend(textwrap.wrap(stripped, width=width, subsequent_indent="  ") or [""])
            continue
        cleaned = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", stripped)
        cleaned = cleaned.replace("`", "")
        prefix = ""
        if cleaned.startswith("#"):
            level = len(cleaned) - len(cleaned.lstrip("#"))
            cleaned = cleaned[level:].strip().upper() if level == 1 else cleaned[level:].strip()
            prefix = "" if level == 1 else "• "
        wrapped = textwrap.wrap(cleaned, width=width, initial_indent=prefix, subsequent_indent="  ")
        lines.extend(wrapped or [""])
    return lines


def render_pdf(markdown_path: Path, output: Path, status: str, release_version: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    lines = markdown_lines(markdown_path.read_text(encoding="utf-8"))
    page_size = 47
    with PdfPages(output) as pdf:
        for page_number, offset in enumerate(range(0, max(len(lines), 1), page_size), start=1):
            fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
            fig.text(0.07, 0.965, f"Claim Review Workbench · {status.upper()} · {release_version}", fontsize=8, color="#52666a")
            y = 0.93
            for line in lines[offset:offset + page_size]:
                size = 11 if line.isupper() and line else 9
                weight = "bold" if size == 11 else "normal"
                fig.text(0.07, y, line, fontsize=size, fontweight=weight, family="DejaVu Sans", va="top")
                y -= 0.0185 if line else 0.012
            fig.text(0.5, 0.025, f"{markdown_path.name} · trang {page_number}", ha="center", fontsize=7, color="#6c7b7d")
            plt.axis("off")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)


def build(output_root: Path, status: str, release_version: str, confirm_gates: bool = False) -> tuple[Path, Path]:
    if status == "final" and not confirm_gates:
        raise ValueError("FINAL requires --confirm-gates after completing 07_RELEASE_SECURITY_AND_UAT.md and 08_DEFINITION_OF_DONE.md.")
    if status == "final":
        from scripts.check_project_done import evaluate
        done = evaluate(level="research_handoff")
        if not done["done"]:
            raise ValueError("FINAL Definition of Done is not satisfied: " + ", ".join(done["blockers"]))
    missing = [str(path) for path in NUMBERED_DOCS + SUPPORT_FILES if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing handoff inputs:\n" + "\n".join(missing))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_name = f"AI_INSURANCE_HANDOFF_{release_version}_{status.upper()}_{stamp}"
    package = output_root / package_name
    if package.exists():
        shutil.rmtree(package)
    (package / "00-08_HANDBOOK").mkdir(parents=True)
    (package / "90_CONTRACTS").mkdir()
    (package / "99_STATUS").mkdir()

    for source in NUMBERED_DOCS:
        shutil.copy2(source, package / "00-08_HANDBOOK" / source.name)
        render_pdf(source, package / "00-08_HANDBOOK" / source.with_suffix(".pdf").name, status, release_version)
    for source in SUPPORT_FILES[:3]:
        shutil.copy2(source, package / "90_CONTRACTS" / source.name)
    shutil.copy2(SUPPORT_FILES[3], package / "99_STATUS" / SUPPORT_FILES[3].name)

    manifest = {
        "package": package_name,
        "status": status,
        "release_version": release_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "final_gates_confirmed": bool(confirm_gates),
        "warning": None if status == "final" else "DRAFT package; not approved for production use.",
    }
    (package / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in package.rglob("*") if path.is_file())
    checksum_lines = [f"{sha256(path)}  {path.relative_to(package).as_posix()}" for path in files]
    (package / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    archive = output_root / f"{package_name}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                bundle.write(path, Path(package_name) / path.relative_to(package))
    return package, archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=("draft", "final"), default="draft")
    parser.add_argument("--release-version", default="research-v1")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--confirm-gates", action="store_true")
    args = parser.parse_args()
    package, archive = build(args.output_dir, args.status, args.release_version, args.confirm_gates)
    print(f"Package: {package}")
    print(f"ZIP: {archive}")
    print(f"ZIP SHA-256: {sha256(archive)}")


if __name__ == "__main__":
    main()

