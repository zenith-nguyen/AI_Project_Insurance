"""Export the stable API contract for prototype and integration teams."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.app import app  # noqa: E402


OUTPUT = ROOT / "contracts" / "claim_review_openapi.v1.json"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {OUTPUT}")


if __name__ == "__main__":
    main()
