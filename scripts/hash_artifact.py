"""Compute the file or deterministic directory SHA-256 used by release gates."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError(f"Artifact directory contains no files: {root}")
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(bytes.fromhex(file_hash(path)))
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected")
    args = parser.parse_args()

    path = args.path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    actual = tree_hash(path) if path.is_dir() else file_hash(path)
    print(actual)
    if args.expected and actual.casefold() != args.expected.casefold():
        raise SystemExit(f"HASH MISMATCH: expected {args.expected}, got {actual}")
    if args.expected:
        print("Artifact hash: PASS")


if __name__ == "__main__":
    main()
