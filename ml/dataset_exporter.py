"""Dataset exporter for YOLO/vision training with perceptual-hash dedup.

This module builds a local dataset from already-scraped images without touching
the scraping pipeline. It performs:
- File-level hash and perceptual-hash (pHash) computation
- Near-duplicate suppression using Hamming distance threshold
- Optional metadata join from DB for labels/attributes
- Train/val split
- Label Studio import JSON generation (for human review)

Outputs under `datasets/yolo_cars/<run_id>/`:
- images/train, images/val (symlink or copies)
- metadata.csv (path, hashes, db fields)
- dedup_index.json (pHash clusters)
- labelstudio_import.json (basic import with image paths)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image
import imagehash  # type: ignore

try:
    # Optional DB access; if unavailable, we still export from the filesystem
    from sqlalchemy.orm import Session
    from db.database import SessionLocal  # type: ignore
    from db.models import CarAdRaw  # type: ignore
except Exception:  # pragma: no cover
    Session = None  # type: ignore
    SessionLocal = None  # type: ignore
    CarAdRaw = None  # type: ignore


@dataclass
class ImageRecord:
    local_path: Path
    file_hash: str
    phash: str
    ad_id: Optional[int]
    make: Optional[str]
    model: Optional[str]
    year: Optional[int]


def compute_file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_phash(path: Path) -> str:
    # Use 16x16 hash for finer granularity
    with Image.open(path) as img:
        img = img.convert("RGB")
        ph = imagehash.phash(img, hash_size=16)
        return str(ph)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    # imagehash outputs hex string; convert to int for Hamming
    a_int = int(hash_a, 16)
    b_int = int(hash_b, 16)
    return (a_int ^ b_int).bit_count()


def scan_images(images_root: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if not images_root.exists():
        return []
    return [p for p in images_root.iterdir() if p.is_file() and p.suffix.lower() in exts]


def load_db_index() -> Dict[str, Dict]:
    """Map local image path → DB row info, if DB is available.

    Falls back to empty mapping when DB is not configured.
    """
    if SessionLocal is None or CarAdRaw is None:
        return {}
    mapping: Dict[str, Dict] = {}
    db: Session = SessionLocal()  # type: ignore
    try:
        ads = db.query(CarAdRaw).all()
        for ad in ads:
            for p in (ad.local_image_paths or []):
                mapping[os.path.abspath(p)] = {
                    "ad_id": ad.id,
                    "make": ad.make,
                    "model": ad.model,
                    "year": ad.year,
                }
    finally:
        try:
            db.close()
        except Exception:
            pass
    return mapping


def build_records(images: List[Path], db_index: Dict[str, Dict]) -> List[ImageRecord]:
    records: List[ImageRecord] = []
    for p in images:
        try:
            file_hash = compute_file_hash(p)
            phash = compute_phash(p)
            db_row = db_index.get(str(p.resolve()))
            records.append(
                ImageRecord(
                    local_path=p,
                    file_hash=file_hash,
                    phash=phash,
                    ad_id=(db_row or {}).get("ad_id"),
                    make=(db_row or {}).get("make"),
                    model=(db_row or {}).get("model"),
                    year=(db_row or {}).get("year"),
                )
            )
        except Exception:
            # Skip unreadable images
            continue
    return records


def deduplicate(records: List[ImageRecord], max_hamming_distance: int = 10) -> Tuple[List[ImageRecord], Dict[str, List[str]]]:
    """Suppress near-duplicates.

    Returns kept records and clusters as dict: representative_phash → list of member file paths.
    """
    kept: List[ImageRecord] = []
    clusters: Dict[str, List[str]] = {}
    for rec in sorted(records, key=lambda r: r.local_path.name):
        is_dup = False
        for k in kept:
            if rec.file_hash == k.file_hash:
                is_dup = True
                clusters.setdefault(k.phash, []).append(str(rec.local_path))
                break
            if hamming_distance(rec.phash, k.phash) <= max_hamming_distance:
                is_dup = True
                clusters.setdefault(k.phash, []).append(str(rec.local_path))
                break
        if not is_dup:
            kept.append(rec)
            clusters.setdefault(rec.phash, []).append(str(rec.local_path))
    return kept, clusters


def write_metadata_csv(out_csv: Path, records: List[ImageRecord]) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["local_path", "file_hash", "phash", "ad_id", "make", "model", "year"])
        for r in records:
            writer.writerow([
                str(r.local_path),
                r.file_hash,
                r.phash,
                r.ad_id or "",
                r.make or "",
                r.model or "",
                r.year or "",
            ])


def write_labelstudio_import(out_json: Path, records: List[ImageRecord]) -> None:
    """Create a minimal Label Studio import file (no annotations yet)."""
    tasks = []
    for r in records:
        tasks.append({
            "data": {"image": str(r.local_path.resolve())},
            "meta": {
                "ad_id": r.ad_id,
                "make": r.make,
                "model": r.model,
                "year": r.year,
            },
        })
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(tasks, f, indent=2)


def materialize_dataset(run_id: Optional[str] = None, images_root: Optional[Path] = None, train_ratio: float = 0.9) -> Dict[str, str]:
    """Build a YOLO-friendly dataset directory from local scraped images.

    Returns paths to key outputs.
    """
    run_id = run_id or os.environ.get("DATASET_RUN_ID") or f"run_{os.getpid()}"
    images_root = images_root or Path("scraped_images/images")

    out_root = Path("datasets") / "yolo_cars" / run_id
    images_out = out_root / "images"
    train_dir = images_out / "train"
    val_dir = images_out / "val"
    out_root.mkdir(parents=True, exist_ok=True)
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    db_index = load_db_index()
    found = scan_images(images_root)
    records = build_records(found, db_index)
    kept, clusters = deduplicate(records)

    # Shuffle and split
    rng = random.Random(42)
    rng.shuffle(kept)
    split_idx = int(len(kept) * train_ratio)
    train_set = kept[:split_idx]
    val_set = kept[split_idx:]

    # Link images (use symlinks to save space; fall back to copy on error)
    def link_set(items: List[ImageRecord], target_dir: Path) -> int:
        count = 0
        for rec in items:
            target = target_dir / rec.local_path.name
            try:
                if target.exists():
                    continue
                os.symlink(rec.local_path.resolve(), target)
            except Exception:
                # Fallback: copy
                try:
                    import shutil
                    shutil.copyfile(rec.local_path, target)
                except Exception:
                    continue
            count += 1
        return count

    n_train = link_set(train_set, train_dir)
    n_val = link_set(val_set, val_dir)

    # Write artifacts
    write_metadata_csv(out_root / "metadata.csv", kept)
    with open(out_root / "dedup_index.json", "w") as f:
        json.dump(clusters, f, indent=2)
    write_labelstudio_import(out_root / "labelstudio_import.json", kept)

    return {
        "root": str(out_root),
        "train_dir": str(train_dir),
        "val_dir": str(val_dir),
        "metadata_csv": str(out_root / "metadata.csv"),
        "dedup_index": str(out_root / "dedup_index.json"),
        "labelstudio_import": str(out_root / "labelstudio_import.json"),
    }


if __name__ == "__main__":
    outputs = materialize_dataset()
    print(json.dumps(outputs, indent=2))


