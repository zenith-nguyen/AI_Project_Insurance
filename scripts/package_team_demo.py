"""Create a small shareable progress-report and synthetic-demo bundle."""
from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist/CLAIM_REVIEW_TEAM_DEMO_2026-10-13.zip"
FILES = [
    "reports/00_README_BAO_CAO_TIEN_DO_2.md",
    "reports/PROGRESS_REPORT_2_MASTER_2026-10-13.md",
    "reports/PROGRESS_REPORT_2_MASTER_2026-10-13.html",
    "reports/PROGRESS_REPORT_2_MASTER_2026-10-13.pdf",
    "prototype/demo_assets/workbench_overview.png",
    "prototype/demo_assets/workbench_evidence.png",
    "prototype/demo_assets/synthetic_vehicle_collision.png",
    "prototype/demo_assets/synthetic_repair_estimate.png",
    "docs/handbook/02_INSTALLATION_AND_QUICKSTART.md",
]


def main() -> None:
    missing = [relative for relative in FILES if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"Cannot package missing demo files: {missing}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as bundle:
        for relative in FILES:
            bundle.write(ROOT / relative, relative)
        bundle.writestr(
            "00_START_HERE.txt",
            "TEAM DEMO · 13/10/2026\n"
            "Open reports/PROGRESS_REPORT_2_MASTER_2026-10-13.pdf first.\n"
            "Images and document in prototype/demo_assets are synthetic.\n"
            "The screenshots show a local research demo; YOLO and OCR/KIE checkpoints were not active.\n"
            "To run the live UI, clone the repository and follow docs/handbook/02_INSTALLATION_AND_QUICKSTART.md.\n",
        )
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"Bundle: {OUTPUT}")
    print(f"Files: {len(FILES) + 1}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
