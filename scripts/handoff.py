"""Cross-platform preflight, startup and smoke test for the handoff demo.

This command intentionally manages only the fixture Docker application. It never
deletes volumes, downloads private artifacts or changes host configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose.yaml"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
SMOKE_PATHS = (
    "/health",
    "/readiness",
    "/version",
    "/system/model-evidence",
    "/system/improvement-status",
    "/system/operations",
    "/docs",
    "/",
)


def _run(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _command_version(command: list[str], *, timeout: int = 8) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "version": None, "error": f"Không tìm thấy {command[0]} trong PATH."}
    try:
        result = _run(command, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"available": False, "version": None, "error": str(error)}
    output = (result.stdout or result.stderr).strip().splitlines()
    return {
        "available": result.returncode == 0,
        "version": output[0] if output else None,
        "error": None if result.returncode == 0 else "\n".join(output[-3:]),
    }


def collect_preflight() -> dict[str, Any]:
    system = platform.system()
    machine = platform.machine().lower()
    disk = shutil.disk_usage(ROOT)
    docker = _command_version(["docker", "version", "--format", "{{.Server.Version}}"])
    compose = _command_version(["docker", "compose", "version", "--short"])
    checks = {
        "compose_file": COMPOSE_FILE.is_file(),
        "docker_engine": docker["available"],
        "docker_compose": compose["available"],
        "disk_free_at_least_3_gb": disk.free >= 3 * 1024**3,
        "port_8000_not_prevalidated": True,
    }
    warnings: list[str] = []
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        warnings.append(
            "macOS Apple Silicon: bản fixture Docker được hỗ trợ; full multimodal live cần kiểm tra wheel "
            "Paddle/PyTorch và checkpoint trên đúng kiến trúc trước khi bàn giao."
        )
    if system == "Darwin":
        warnings.append("macOS không có CUDA; inference nặng có thể dùng CPU/MPS khi adapter hỗ trợ và phải benchmark riêng.")
    if not docker["available"]:
        warnings.append("Docker engine chưa chạy. Mở Docker Desktop rồi chạy lại lệnh này.")
    if disk.free < 3 * 1024**3:
        warnings.append("Ổ đĩa còn dưới 3 GB; Docker build có thể thất bại.")
    return {
        "schema_version": "1.0",
        "platform": {"system": system, "release": platform.release(), "machine": machine},
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "docker": docker,
        "compose": compose,
        "disk": {"free_bytes": disk.free, "free_gb": round(disk.free / 1024**3, 2)},
        "checks": checks,
        "demo_ready": all(checks[name] for name in ("compose_file", "docker_engine", "docker_compose", "disk_free_at_least_3_gb")),
        "scope": "fixture UI/API; không yêu cầu raw data, checkpoint hoặc GPU",
        "warnings": warnings,
    }


def _fetch(base_url: str, path: str, timeout: float = 8) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(256)
            return {
                "url": url,
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "body_preview": body.decode("utf-8", errors="replace")[:120],
            }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"url": url, "ok": False, "status": None, "error": str(error)}


def smoke(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    checks = [_fetch(base_url, path) for path in SMOKE_PATHS]
    return {"base_url": base_url, "passed": all(item["ok"] for item in checks), "checks": checks}


def wait_until_healthy(base_url: str, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _fetch(base_url, "/health", timeout=3)["ok"]:
            return True
        time.sleep(2)
    return False


def write_report(name: str, payload: dict[str, Any]) -> Path:
    target = ROOT / "runtime" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def docker_up(base_url: str, timeout_seconds: int) -> dict[str, Any]:
    preflight = collect_preflight()
    write_report("handoff_preflight.json", preflight)
    if not preflight["demo_ready"]:
        raise RuntimeError("Preflight chưa PASS. Mở Docker Desktop/giải phóng dung lượng rồi chạy lại.")
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"docker compose up thất bại với exit code {result.returncode}.")
    if not wait_until_healthy(base_url, timeout_seconds):
        raise RuntimeError(f"API chưa healthy sau {timeout_seconds} giây. Chạy `docker compose logs claim-review`.")
    report = smoke(base_url)
    write_report("handoff_smoke.json", report)
    return report


def docker_down() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"docker compose down thất bại với exit code {result.returncode}.")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "up", "smoke", "down"))
    parser.add_argument("--base-url", default=os.getenv("INSURANCE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            report = collect_preflight()
            write_report("handoff_preflight.json", report)
            print_json(report)
            raise SystemExit(0 if report["demo_ready"] else 2)
        if args.command == "up":
            report = docker_up(args.base_url, args.timeout)
            print_json(report)
            print(f"\nMở ứng dụng: {args.base_url}/")
            print(f"API docs: {args.base_url}/docs")
            return
        if args.command == "smoke":
            report = smoke(args.base_url)
            write_report("handoff_smoke.json", report)
            print_json(report)
            raise SystemExit(0 if report["passed"] else 1)
        docker_down()
        print("Đã dừng container. Không xóa volume hoặc dữ liệu.")
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"HANDOFF ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
