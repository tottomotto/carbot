"""Scan local images and infer dominant body color using HSV masks.

This utility walks a directory of images (e.g., `scraped_images/images`),
computes a dominant color and confidence per image, and prints a concise
report. Intended as a lightweight heuristic until a detector is integrated.
"""
import argparse
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def infer_dominant_color(image_path: str) -> Tuple[Optional[str], float]:
    """Return (color_name, confidence 0..1) from image using HSV masks.

    The heuristic counts pixels inside coarse HSV ranges for common car colors
    and selects the color with the highest count. Confidence is the fraction of
    pixels within the winning mask.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    # Resize to speed up processing on high-res images
    height, width = img.shape[:2]
    scale = 256 / max(height, width)
    if scale < 1.0:
        img = cv2.resize(img, (int(width * scale), int(height * scale)))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # H: 0..179, S: 0..255, V: 0..255
    ranges: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
        "black": ((0, 0, 0), (179, 60, 70)),
        "white": ((0, 0, 200), (179, 40, 255)),
        "gray": ((0, 0, 70), (179, 40, 200)),
        "red": ((0, 80, 80), (10, 255, 255)),
        "red2": ((170, 80, 80), (179, 255, 255)),  # wrap-around
        "blue": ((100, 80, 80), (130, 255, 255)),
        "green": ((40, 80, 80), (80, 255, 255)),
        "yellow": ((20, 80, 80), (35, 255, 255)),
        "brown": ((10, 80, 40), (20, 255, 180)),
        "silver": ((0, 0, 140), (179, 30, 230)),
    }

    counts: Dict[str, int] = {}
    total_pixels = hsv.shape[0] * hsv.shape[1]

    for name, (lo, hi) in ranges.items():
        lo_arr = np.array(lo, dtype=np.uint8)
        hi_arr = np.array(hi, dtype=np.uint8)
        mask = cv2.inRange(hsv, lo_arr, hi_arr)
        counts[name] = int(np.count_nonzero(mask))

    # Combine wrap-around reds
    if "red" in counts and "red2" in counts:
        counts["red"] = counts["red"] + counts["red2"]
        counts.pop("red2", None)

    if total_pixels == 0 or not counts:
        return None, 0.0

    top_color = max(counts, key=counts.get)
    confidence = counts[top_color] / float(total_pixels)

    # Clamp and normalize
    confidence = round(min(max(confidence, 0.0), 1.0), 3)

    # Normalize ambiguous low-confidence silver to gray
    if top_color == "silver" and confidence < 0.05:
        top_color = "gray"

    return top_color, confidence


def iter_image_paths(root_dir: Path) -> Iterable[Path]:
    for path in sorted(root_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def scan_directory(dir_path: Path) -> List[Tuple[str, Optional[str], float]]:
    results: List[Tuple[str, Optional[str], float]] = []
    for img_path in iter_image_paths(dir_path):
        color, conf = infer_dominant_color(str(img_path))
        results.append((img_path.name, color, conf))
    return results


def print_report(results: List[Tuple[str, Optional[str], float]]) -> None:
    if not results:
        print("No images found.")
        return

    updated = 0
    for filename, color, conf in results:
        color_display = color or "unknown"
        print(f"{filename}: {color_display} ({conf:.3f})")
        if color:
            updated += 1

    print(f"Total images: {len(results)}, Classified: {updated}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Infer dominant colors for images in a folder")
    parser.add_argument(
        "--dir",
        dest="dir",
        default=str(Path("scraped_images") / "images"),
        help="Directory containing images (default: scraped_images/images)",
    )
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        print(f"Directory not found: {root}")
        return

    results = scan_directory(root)
    print_report(results)


if __name__ == "__main__":
    main()


