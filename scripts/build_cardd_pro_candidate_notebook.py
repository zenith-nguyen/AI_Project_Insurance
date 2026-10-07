"""Add account-switch preflight cells to the locked CarDD candidate notebook."""
from __future__ import annotations

import json
from pathlib import Path


SOURCE = Path("notebooks/CarDD_YOLOv8s_Candidate_v1.ipynb")
OUTPUT = Path("notebooks/CarDD_YOLOv8s_Candidate_Pro_Account_v2.ipynb")


def markdown(value: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in value.strip().splitlines()],
    }


def code(value: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in value.strip().splitlines()],
    }


def build() -> None:
    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
    account_cells = [
        markdown(
            """# Thiết lập tài khoản Colab Pro

Notebook này dành cho runtime đăng nhập bằng `hoanganhthu01230@gmail.com`.

Trước khi bấm **Run all**, tài khoản mới phải có hai shortcut ở **My Drive** với đúng tên:

- `AI_Project_Insurance`: code, labels, reports và checkpoints đang dùng.
- `AI_Project_Insurance_OLD`: nguồn ảnh Bronze CarDD.

Hãy chia sẻ trực tiếp hai thư mục gốc cho tài khoản mới với quyền **Editor**, rồi mở **Shared with me → Organize → Add shortcut → My Drive**. Chia sẻ riêng shortcut cũ có thể không cấp quyền vào thư mục gốc mà shortcut trỏ tới."""
        ),
        markdown("## 0. Gắn Drive và kiểm tra quyền của tài khoản mới"),
        code(
            """from pathlib import Path

from google.colab import drive

DRIVE_ROOT = Path("/content/drive")
MY_DRIVE = DRIVE_ROOT / "MyDrive"

if not MY_DRIVE.is_dir():
    drive.mount(str(DRIVE_ROOT), force_remount=False)

NEW_PROJECT_PREFLIGHT = MY_DRIVE / "AI_Project_Insurance"
OLD_PROJECT_PREFLIGHT = MY_DRIVE / "AI_Project_Insurance_OLD"

required = {
    "active project": NEW_PROJECT_PREFLIGHT,
    "Bronze project": OLD_PROJECT_PREFLIGHT,
    "Bronze images": OLD_PROJECT_PREFLIGHT / "data/bronze/layerA_cardd/data",
    "split manifest": NEW_PROJECT_PREFLIGHT / "data/processed/cardd_yolo_v1/split_manifest.jsonl",
    "baseline checkpoint": NEW_PROJECT_PREFLIGHT / "artifacts/image/cardd_yolov8n_seg_baseline_v2/weights/best.pt",
    "baseline validation": NEW_PROJECT_PREFLIGHT / "reports/metrics/cardd_yolov8n_seg_val_v2.json",
}
missing = {name: str(path) for name, path in required.items() if not path.exists()}
if missing:
    details = "\\n".join(f"- {name}: {path}" for name, path in missing.items())
    raise FileNotFoundError(
        "Tài khoản mới chưa thấy đủ dữ liệu. Hãy thêm hai shortcut vào My Drive rồi chạy lại cell:\\n"
        + details
    )

probe = NEW_PROJECT_PREFLIGHT / ".colab_pro_write_test.tmp"
try:
    probe.write_text("write-access-ok", encoding="utf-8")
    assert probe.read_text(encoding="utf-8") == "write-access-ok"
finally:
    probe.unlink(missing_ok=True)

print("Drive shortcuts: PASS")
print("Read access: PASS")
print("Write access: PASS")
print("Active project:", NEW_PROJECT_PREFLIGHT)
print("Bronze source:", OLD_PROJECT_PREFLIGHT)"""
        ),
    ]

    notebook["cells"] = account_cells + notebook["cells"]
    notebook["metadata"].setdefault("colab", {})["name"] = OUTPUT.name
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
