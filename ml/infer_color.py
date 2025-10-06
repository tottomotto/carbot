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
    """Return (color_name, confidence 0..1) using foreground mask + k-means on HSV.

    Steps:
    1) Downscale for speed
    2) Foreground segmentation via GrabCut (rect init)
    3) K-means clustering on HSV of foreground pixels (k=3)
    4) Map cluster centroids to coarse human colors; confidence = cluster share
    Fallback: simple HSV range counting when segmentation/clustering fails.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    height, width = img.shape[:2]
    scale = 320 / max(height, width)
    if scale < 1.0:
        img = cv2.resize(img, (int(width * scale), int(height * scale)))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    def fallback_ranges(hsv_img: np.ndarray) -> Tuple[Optional[str], float]:
        ranges: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
            "black": ((0, 0, 0), (179, 60, 70)),
            "white": ((0, 0, 200), (179, 40, 255)),
            "gray": ((0, 0, 70), (179, 40, 200)),
            "red": ((0, 80, 80), (10, 255, 255)),
            "red2": ((170, 80, 80), (179, 255, 255)),
            "blue": ((100, 80, 80), (130, 255, 255)),
            "green": ((40, 80, 80), (80, 255, 255)),
            "yellow": ((20, 80, 80), (35, 255, 255)),
            "brown": ((10, 80, 40), (20, 255, 180)),
            "silver": ((0, 0, 140), (179, 30, 230)),
        }
        counts: Dict[str, int] = {}
        total_pixels = hsv_img.shape[0] * hsv_img.shape[1]
        for name, (lo, hi) in ranges.items():
            lo_arr = np.array(lo, dtype=np.uint8)
            hi_arr = np.array(hi, dtype=np.uint8)
            mask = cv2.inRange(hsv_img, lo_arr, hi_arr)
            counts[name] = int(np.count_nonzero(mask))
        if "red" in counts and "red2" in counts:
            counts["red"] = counts["red"] + counts["red2"]
            counts.pop("red2", None)
        if total_pixels == 0 or not counts:
            return None, 0.0
        top_color = max(counts, key=counts.get)
        conf = counts[top_color] / float(total_pixels)
        conf = round(min(max(conf, 0.0), 1.0), 3)
        if top_color == "silver" and conf < 0.05:
            top_color = "gray"
        return top_color, conf

    # Foreground segmentation via GrabCut (rectangular init)
    try:
        mask = np.zeros(img.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        pad_h = int(img.shape[0] * 0.06)
        pad_w = int(img.shape[1] * 0.06)
        rect = (pad_w, pad_h, img.shape[1] - 2 * pad_w, img.shape[0] - 2 * pad_h)
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 3, cv2.GC_INIT_WITH_RECT)
        fg_mask = np.where((mask == 1) | (mask == 3), 1, 0).astype("uint8")
        # If foreground too small, fallback
        if int(fg_mask.sum()) < (img.shape[0] * img.shape[1] * 0.05):
            return fallback_ranges(hsv)
        fg_pixels = hsv[fg_mask == 1]
        # Downsample pixels for k-means speed
        if fg_pixels.shape[0] > 5000:
            idx = np.random.choice(fg_pixels.shape[0], 5000, replace=False)
            fg_pixels = fg_pixels[idx]

        # K-means on HSV (convert to float32)
        Z = fg_pixels.astype(np.float32)
        K = 3
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        compactness, labels, centers = cv2.kmeans(Z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        labels = labels.flatten()
        centers = centers.astype(np.float32)

        # Choose largest cluster
        counts = np.bincount(labels, minlength=K)
        top_cluster = int(np.argmax(counts))
        center = centers[top_cluster]
        cluster_share = counts[top_cluster] / float(counts.sum())

        # Map HSV centroid to coarse color name
        h, s, v = center.tolist()
        color = _map_hsv_to_color(h, s, v)
        conf = round(float(cluster_share), 3)
        return color, conf
    except Exception:
        # Any failure falls back to range method
        return fallback_ranges(hsv)


def _map_hsv_to_color(h: float, s: float, v: float) -> str:
    """Map HSV centroid to a coarse color name.
    Priority order handles grayscale vs chromatic decisions first.
    """
    if v < 60:
        return "black"
    if s < 25 and v > 200:
        return "white"
    if s < 35:
        # mid saturation → gray/silver by brightness
        return "silver" if v > 170 else "gray"

    # Chromatic mapping by hue
    if (h <= 10) or (h >= 170):
        return "red"
    if 15 <= h <= 30:
        return "yellow" if v > 120 else "brown"
    if 35 <= h <= 85:
        return "green"
    if 90 <= h <= 140:
        return "blue"

    return "gray"


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


