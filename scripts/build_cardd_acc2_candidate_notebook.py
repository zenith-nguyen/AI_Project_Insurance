"""Build the CarDD candidate notebook for the renamed Acc 2 Drive folder."""
from __future__ import annotations

import json
from pathlib import Path


SOURCE = Path("notebooks/CarDD_YOLOv8s_Candidate_Pro_Account_v2.ipynb")
OUTPUT = Path("notebooks/CarDD_YOLOv8s_Candidate_Acc2_v3.ipynb")
OLD_ACTIVE_NAME = "AI_Project_Insurance"
NEW_ACTIVE_NAME = "AI_Project_Insurance_Acc 2"


def build() -> None:
    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))

    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        # Quoted Python paths identify only the active project. The Bronze folder
        # ends in _OLD and therefore is intentionally not changed by this match.
        source = source.replace(
            f'{OLD_ACTIVE_NAME}"',
            f'{NEW_ACTIVE_NAME}"',
        )
        source = source.replace(
            f'`{OLD_ACTIVE_NAME}`: code, labels, reports',
            f'`{NEW_ACTIVE_NAME}`: code, labels, reports',
        )
        cell["source"] = [line + "\n" for line in source.rstrip("\n").splitlines()]

    notebook["cells"].insert(
        0,
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Bản v3 cho thư mục `AI_Project_Insurance_Acc 2`\n",
                "\n",
                "Toàn bộ output candidate, report và checkpoint sẽ được ghi vào thư mục này. "
                "Nguồn Bronze tiếp tục đọc từ `AI_Project_Insurance_OLD`.\n",
            ],
        },
    )
    notebook["metadata"].setdefault("colab", {})["name"] = OUTPUT.name
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
