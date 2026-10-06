"""Convert the verified CarDD FiftyOne export to an Ultralytics segmentation dataset."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import random
import shutil
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image


CLASS_NAMES = ["crack", "dent", "glass shatter", "lamp broken", "scratch", "tire flat"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_mask(value: dict[str, Any]) -> np.ndarray:
    wrapper = value.get("$binary")
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("base64"), str):
        raise ValueError("Expected canonical Extended JSON $binary with a base64 payload")
    raw = base64.b64decode(wrapper["base64"])
    array = np.load(io.BytesIO(zlib.decompress(raw)), allow_pickle=False)
    if array.ndim != 2:
        raise ValueError(f"Expected a 2D mask, found shape {array.shape}")
    unique = set(np.unique(array).tolist())
    if not unique.issubset({False, True, 0, 1}):
        raise ValueError(f"Mask is not binary: {sorted(unique)}")
    return np.ascontiguousarray(array.astype(np.uint8))


def mask_to_polygon(mask: np.ndarray, bbox: list[float]) -> tuple[np.ndarray, int]:
    import cv2
    from ultralytics.utils.ops import masks2segments

    contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    if not contours:
        raise ValueError("Mask has no external contour")
    segment = masks2segments(mask[None, :, :], strategy="all")[0]
    if segment.shape[0] < 3:
        raise ValueError("Mask polygon contains fewer than three points")
    x, y, width, height = map(float, bbox)
    mask_height, mask_width = mask.shape
    polygon = np.empty_like(segment, dtype=np.float64)
    polygon[:, 0] = x + ((segment[:, 0] + 0.5) / mask_width) * width
    polygon[:, 1] = y + ((segment[:, 1] + 0.5) / mask_height) * height
    polygon = np.clip(polygon, 0.0, 1.0)
    return polygon, len(contours)


def dhash(path: Path) -> tuple[int, float]:
    with Image.open(path) as image:
        width, height = image.size
        pixels = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS))
    bits = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in bits.ravel():
        value = (value << 1) | int(bit)
    return value, width / height


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def duplicate_groups(image_paths: list[Path], max_hamming: int) -> list[list[int]]:
    signatures = [dhash(path) for path in image_paths]
    union = UnionFind(len(image_paths))
    for left in range(len(image_paths)):
        left_hash, left_ratio = signatures[left]
        for right in range(left + 1, len(image_paths)):
            right_hash, right_ratio = signatures[right]
            if abs(left_ratio - right_ratio) > 0.01:
                continue
            if (left_hash ^ right_hash).bit_count() <= max_hamming:
                union.union(left, right)
    grouped: dict[int, list[int]] = {}
    for index in range(len(image_paths)):
        grouped.setdefault(union.find(index), []).append(index)
    return list(grouped.values())


def assign_groups(
    groups: list[list[int]],
    class_vectors: np.ndarray,
    fractions: tuple[float, float, float],
    seed: int,
) -> dict[int, str]:
    names = ("train", "val", "test")
    total_images = len(class_vectors)
    total_classes = class_vectors.sum(axis=0)
    target_images = np.asarray(fractions) * total_images
    target_classes = np.outer(np.asarray(fractions), total_classes)
    current_images = np.zeros(3, dtype=float)
    current_classes = np.zeros((3, class_vectors.shape[1]), dtype=float)
    rng = random.Random(seed)

    prepared = []
    for group in groups:
        vector = class_vectors[group].sum(axis=0)
        rarity = float(sum(vector / np.maximum(total_classes, 1)))
        prepared.append((group, vector, rarity, rng.random()))
    prepared.sort(key=lambda item: (-item[2], -len(item[0]), item[3]))

    assignments: dict[int, str] = {}
    for group, vector, _, _ in prepared:
        scores = []
        for split_index in range(3):
            candidate_images = current_images.copy()
            candidate_classes = current_classes.copy()
            candidate_images[split_index] += len(group)
            candidate_classes[split_index] += vector
            image_error = np.square((candidate_images - target_images) / np.maximum(target_images, 1)).sum()
            class_error = np.square((candidate_classes - target_classes) / np.maximum(target_classes, 1)).sum()
            overflow = np.maximum(candidate_images - target_images, 0).sum() / total_images
            scores.append(float(image_error + class_error + 5 * overflow))
        chosen = min(range(3), key=lambda index: (scores[index], index))
        current_images[chosen] += len(group)
        current_classes[chosen] += vector
        for image_index in group:
            assignments[image_index] = names[chosen]
    return assignments


def link_image(source: Path, destination: Path, mode: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "copy":
        shutil.copy2(source, destination)
        return "copy"
    if mode in {"auto", "hardlink"}:
        try:
            os.link(source, destination)
            return "hardlink"
        except OSError:
            if mode == "hardlink":
                raise
    if mode in {"auto", "symlink"}:
        try:
            destination.symlink_to(source.resolve())
            if destination.is_file():
                return "symlink"
        except OSError:
            destination.unlink(missing_ok=True)
            if mode == "symlink":
                raise
    shutil.copy2(source, destination)
    return "copy"


def convert(root: Path, output: Path, seed: int, image_mode: str, max_hamming: int) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    payload = json.loads((root / "samples.json").read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("samples")
    if not isinstance(records, list):
        raise ValueError("samples.json does not contain a sample list")
    class_to_id = {name: index for index, name in enumerate(CLASS_NAMES)}
    image_by_name = {
        path.name: path for path in (root / "data").rglob("*")
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    }

    prepared = []
    class_vectors = []
    class_instances: Counter[str] = Counter()
    multi_contour_objects = 0
    max_contours = 0
    for record in records:
        image_name = Path(str(record["filepath"]).replace("\\", "/")).name
        image_path = image_by_name.get(image_name)
        if image_path is None:
            raise FileNotFoundError(f"Missing image referenced by samples.json: {image_name}")
        boxes = record["detections"]["detections"]
        segments = record["segmentations"]["detections"]
        if len(boxes) != len(segments):
            raise ValueError(f"Detection/segmentation count mismatch for {image_name}")
        lines = []
        vector = np.zeros(len(CLASS_NAMES), dtype=int)
        for box, segment in zip(boxes, segments):
            if box.get("label") != segment.get("label") or not np.allclose(
                box.get("bounding_box"), segment.get("bounding_box"), atol=1e-9
            ):
                raise ValueError(f"Detection/segmentation pairing mismatch for {image_name}")
            label = str(segment["label"])
            if label not in class_to_id:
                raise ValueError(f"Unknown CarDD class: {label}")
            mask = decode_mask(segment["mask"])
            polygon, contour_count = mask_to_polygon(mask, segment["bounding_box"])
            multi_contour_objects += int(contour_count > 1)
            max_contours = max(max_contours, contour_count)
            coordinates = " ".join(f"{value:.8f}" for value in polygon.reshape(-1))
            lines.append(f"{class_to_id[label]} {coordinates}")
            vector[class_to_id[label]] += 1
            class_instances[label] += 1
        prepared.append({"image_name": image_name, "image_path": image_path, "label_lines": lines})
        class_vectors.append(vector)

    image_paths = [item["image_path"] for item in prepared]
    groups = duplicate_groups(image_paths, max_hamming=max_hamming)
    assignments = assign_groups(groups, np.asarray(class_vectors), (0.70, 0.15, 0.15), seed)
    output.mkdir(parents=True)
    split_images: Counter[str] = Counter()
    split_instances = {name: Counter() for name in ("train", "val", "test")}
    link_modes: Counter[str] = Counter()
    manifest_rows = []
    for index, item in enumerate(prepared):
        split = assignments[index]
        image_destination = output / "images" / split / item["image_name"]
        label_destination = output / "labels" / split / f"{Path(item['image_name']).stem}.txt"
        link_modes[link_image(item["image_path"], image_destination, image_mode)] += 1
        label_destination.parent.mkdir(parents=True, exist_ok=True)
        label_destination.write_text("\n".join(item["label_lines"]) + "\n", encoding="utf-8")
        split_images[split] += 1
        for class_id, count in enumerate(class_vectors[index]):
            split_instances[split][CLASS_NAMES[class_id]] += int(count)
        manifest_rows.append({"image": item["image_name"], "split": split, "instances": int(sum(class_vectors[index]))})

    data_yaml = {
        "path": str(output.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(CLASS_NAMES)},
    }
    (output / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (output / "split_manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest_rows), encoding="utf-8"
    )
    duplicate_group_sizes = sorted((len(group) for group in groups if len(group) > 1), reverse=True)
    groups_crossing_splits = sum(
        len({assignments[index] for index in group}) > 1 for group in groups
    )
    report = {
        "source": str(root.resolve()),
        "samples_json_sha256": sha256(root / "samples.json"),
        "output": str(output.resolve()),
        "seed": seed,
        "split_fractions": {"train": 0.70, "val": 0.15, "test": 0.15},
        "classes": CLASS_NAMES,
        "images": len(prepared),
        "instances": int(sum(class_instances.values())),
        "class_instances": dict(class_instances),
        "split_images": dict(split_images),
        "split_instances": {name: dict(counts) for name, counts in split_instances.items()},
        "near_duplicate_hash_threshold": max_hamming,
        "duplicate_group_count": sum(len(group) > 1 for group in groups),
        "duplicate_group_sizes": duplicate_group_sizes,
        "duplicate_groups_cross_split": groups_crossing_splits,
        "multi_contour_objects_merged": multi_contour_objects,
        "maximum_contours_in_one_object": max_contours,
        "image_materialization_modes": dict(link_modes),
    }
    (output / "conversion_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cardd_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20261006)
    parser.add_argument("--image-mode", choices=("auto", "hardlink", "symlink", "copy"), default="auto")
    parser.add_argument("--near-duplicate-hamming", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(
        convert(args.cardd_root.resolve(), args.output.resolve(), args.seed, args.image_mode, args.near_duplicate_hamming),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
