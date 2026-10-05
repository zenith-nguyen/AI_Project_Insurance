r"""
Layer C synthetic image generator — scenarios 3, 4, 5 and 8.

FOR A NON-PROGRAMMER
1. Put source images in one folder, for example: input_images/
2. Open PowerShell in the project folder and run:

   .\.venv\Scripts\python.exe reports\handoff\layer_c_scenario_script.py input_images output_layer_c

3. Results appear in four subfolders plus output_layer_c/manifest.csv.

OUTPUT COUNT FOR N VALID INPUT IMAGES
- Scenario 3, plate-region swap: N outputs if N >= 2; otherwise 0.
- Scenario 4, screen-recapture simulation: N outputs.
- Scenario 5, EXIF tampering: N outputs.
- Scenario 8, metadata stripping/re-encode: N outputs.
- Total: 4N outputs when N >= 2; otherwise 3N.

IMPORTANT
- Scenario 3 uses a configurable lower-centre rectangle; it does not detect a real
  number plate. Visually inspect every output or replace the rectangle with verified
  plate annotations before using it for research.
- Scenario 4 approximates display/recapture artefacts; it is not a physical recapture.
- Generated data must be labelled synthetic and kept separate from real test data.
- The script refuses a non-empty output folder unless --overwrite is supplied.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SCENARIO_DIRS = {
    "3_plate_swap": "scenario_03_plate_swap",
    "4_screen_recapture": "scenario_04_screen_recapture",
    "5_exif_tampering": "scenario_05_exif_tampering",
    "8_strip_reencode": "scenario_08_strip_reencode",
}


def find_images(input_dir: Path) -> list[Path]:
    images = sorted(
        path for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    )
    if not images:
        raise FileNotFoundError(f"No supported images found under {input_dir}")
    return images


def validate_box(box: tuple[float, float, float, float]) -> None:
    left, top, right, bottom = box
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("Plate box must be normalized values: 0 <= left < right <= 1 and 0 <= top < bottom <= 1")


def pixel_box(image: Image.Image, box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    width, height = image.size
    left, top, right, bottom = box
    return (
        max(0, round(left * width)),
        max(0, round(top * height)),
        min(width, round(right * width)),
        min(height, round(bottom * height)),
    )


def plate_swap(base: Image.Image, donor: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    output = base.convert("RGB").copy()
    destination_box = pixel_box(output, box)
    donor_patch = donor.convert("RGB").crop(pixel_box(donor, box))
    size = (destination_box[2] - destination_box[0], destination_box[3] - destination_box[1])
    if min(*size, donor_patch.width, donor_patch.height) <= 0:
        raise ValueError("Plate box produced an empty crop")
    donor_patch = donor_patch.resize(size, Image.Resampling.LANCZOS)
    output.paste(donor_patch, destination_box[:2])
    return output


def screen_recapture(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    output = image.convert("RGB")
    width, height = output.size
    scale = float(rng.uniform(0.72, 0.90))
    small = output.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.BILINEAR)
    output = small.resize((width, height), Image.Resampling.BICUBIC)
    output = output.rotate(float(rng.uniform(-0.8, 0.8)), resample=Image.Resampling.BICUBIC, fillcolor=(8, 8, 8))
    array = np.asarray(output, dtype=np.float32)
    yy, xx = np.indices((height, width))
    moire = 5.0 * np.sin(2 * math.pi * (xx + 0.55 * yy) / float(rng.uniform(10, 17)))
    noise = rng.normal(0, 1.8, size=(height, width))
    array += moire[..., None] + noise[..., None]
    array[::3] *= 0.965
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="RGB").filter(ImageFilter.GaussianBlur(0.35))


def synthetic_exif() -> Image.Exif:
    exif = Image.Exif()
    exif[271] = "LAYER_C_SYNTHETIC"  # Make
    exif[272] = "EXIF_TAMPERING_SCENARIO_5"  # Model
    exif[305] = "AI_Project_Insurance synthetic generator"  # Software
    exif[306] = "2030:01:01 00:00:00"  # DateTime
    exif[36867] = "2030:01:01 00:00:00"  # DateTimeOriginal
    return exif


def save_jpeg(image: Image.Image, path: Path, *, quality: int, exif: Image.Exif | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {"format": "JPEG", "quality": quality, "optimize": True}
    if exif is not None:
        options["exif"] = exif
    image.convert("RGB").save(path, **options)


def ensure_output(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(path.is_file() for path in output_dir.rglob("*")) and not overwrite:
        raise FileExistsError(f"Output folder is not empty: {output_dir}. Use --overwrite to replace matching outputs.")
    output_dir.mkdir(parents=True, exist_ok=True)


def generate_variants(
    input_dir: Path,
    output_dir: Path,
    *,
    seed: int = 42,
    plate_box_normalized: tuple[float, float, float, float] = (0.35, 0.68, 0.65, 0.82),
    overwrite: bool = False,
) -> dict[str, int]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)
    validate_box(plate_box_normalized)
    ensure_output(output_dir, overwrite)
    images = find_images(input_dir)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, str]] = []
    counts = {scenario: 0 for scenario in SCENARIO_DIRS}

    for index, source_path in enumerate(images):
        try:
            with Image.open(source_path) as opened:
                source = opened.convert("RGB")
        except Exception as error:
            raise ValueError(f"Cannot read image {source_path}: {error}") from error
        prefix = f"{index + 1:06d}_{source_path.stem}"

        if len(images) >= 2:
            donor_path = images[(index + 1) % len(images)]
            with Image.open(donor_path) as opened:
                donor = opened.convert("RGB")
            destination = output_dir / SCENARIO_DIRS["3_plate_swap"] / f"{prefix}_s03.jpg"
            save_jpeg(plate_swap(source, donor, plate_box_normalized), destination, quality=94)
            rows.append({"scenario": "3_plate_swap", "source": str(source_path), "donor": str(donor_path), "output": str(destination), "synthetic": "true"})
            counts["3_plate_swap"] += 1

        destination = output_dir / SCENARIO_DIRS["4_screen_recapture"] / f"{prefix}_s04.jpg"
        save_jpeg(screen_recapture(source, rng), destination, quality=78)
        rows.append({"scenario": "4_screen_recapture", "source": str(source_path), "donor": "", "output": str(destination), "synthetic": "true"})
        counts["4_screen_recapture"] += 1

        destination = output_dir / SCENARIO_DIRS["5_exif_tampering"] / f"{prefix}_s05.jpg"
        save_jpeg(source, destination, quality=92, exif=synthetic_exif())
        rows.append({"scenario": "5_exif_tampering", "source": str(source_path), "donor": "", "output": str(destination), "synthetic": "true"})
        counts["5_exif_tampering"] += 1

        destination = output_dir / SCENARIO_DIRS["8_strip_reencode"] / f"{prefix}_s08.jpg"
        pixel_copy = Image.fromarray(np.asarray(source, dtype=np.uint8).copy(), mode="RGB")
        save_jpeg(pixel_copy, destination, quality=86)
        rows.append({"scenario": "8_strip_reencode", "source": str(source_path), "donor": "", "output": str(destination), "synthetic": "true"})
        counts["8_strip_reencode"] += 1

    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["scenario", "source", "donor", "output", "synthetic"])
        writer.writeheader()
        writer.writerows(rows)
    return {"input_images": len(images), "total_outputs": len(rows), **counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Layer C synthetic scenarios 3, 4, 5 and 8.")
    parser.add_argument("input_folder", type=Path)
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--plate-box", type=float, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"), default=(0.35, 0.68, 0.65, 0.82))
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    summary = generate_variants(
        arguments.input_folder,
        arguments.output_folder,
        seed=arguments.seed,
        plate_box_normalized=tuple(arguments.plate_box),
        overwrite=arguments.overwrite,
    )
    print("Layer C generation complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
