"""Build a leakage-safe manifest for the media-authenticity benchmark.

Place images as ROOT/<class>/<source_id>__<variant>.<ext>. All variants sharing
source_id are assigned to the same split to prevent transformation leakage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image


CLASSES = {
    "camera_original", "conventional_edit", "social_reencode",
    "screen_recapture", "ai_generated", "ai_edited",
}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def source_id(path: Path) -> str:
    return path.stem.split("__", 1)[0]


def split_for(group: str, seed: int) -> str:
    value = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()[:8], 16) % 100
    return "train" if value < 70 else ("validation" if value < 85 else "test")


def build(root: Path, output: Path, seed: int = 20261013) -> dict:
    rows = []
    corrupt = []
    for label in sorted(CLASSES):
        folder = root / label
        for path in (sorted(folder.rglob("*")) if folder.is_dir() else []):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            try:
                with Image.open(path) as image:
                    image.verify()
            except Exception:
                corrupt.append(str(path.relative_to(root)))
                continue
            group = source_id(path)
            rows.append({
                "path": str(path.resolve()), "relative_path": str(path.relative_to(root)),
                "label": label, "source_group": group, "split": split_for(group, seed),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    group_splits: dict[str, set[str]] = {}
    for row in rows:
        group_splits.setdefault(row["source_group"], set()).add(row["split"])
    leakage = {group: sorted(splits) for group, splits in group_splits.items() if len(splits) > 1}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    report = {
        "valid": bool(rows) and not corrupt and not leakage,
        "seed": seed, "rows": len(rows), "source_groups": len(group_splits),
        "by_label": dict(Counter(row["label"] for row in rows)),
        "by_split": dict(Counter(row["split"] for row in rows)),
        "corrupt": corrupt, "group_leakage": leakage,
        "policy": "All variants of one source image remain in one split.",
    }
    output.with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20261013)
    args = parser.parse_args()
    report = build(args.root, args.output, args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SystemExit("Benchmark manifest gate failed.")


if __name__ == "__main__":
    main()
