"""
RoadPulse AI - Dataset Validator & Integrity Checker
Verifies annotation integrity, split distribution, class consistency,
and checks for data leakage between train, validation, and test sets.
"""

import hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Tuple
from .config_loader import DATASET_DIR, FULL_CLASSES, ACTIVE_ANNOTATED_CLASSES


class DatasetValidator:
    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dataset_dir = Path(dataset_dir)
        self.images_dir = self.dataset_dir / "images"
        self.labels_dir = self.dataset_dir / "labels"

    def _file_hash(self, path: Path) -> str:
        """Calculate SHA256 hash of a file for exact duplicate/leakage detection."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def validate(self) -> Dict[str, Any]:
        """
        Run complete validation:
        1. Existence of splits (train, val, test)
        2. Pair consistency (image without label / label without image)
        3. Class ID extraction and instance counting
        4. Coordinate sanity check (normalized 0-1)
        5. Data leakage check (image content overlap across splits)
        """
        splits = ["train", "val", "test"]
        report: Dict[str, Any] = {
            "dataset_path": str(self.dataset_dir),
            "splits": {},
            "total_images": 0,
            "total_instances": 0,
            "detected_classes": Counter(),
            "data_leakage_detected": False,
            "leakage_details": [],
            "warnings": [],
            "errors": [],
            "is_valid": True,
        }

        split_hashes: Dict[str, Dict[str, Path]] = {"train": {}, "val": {}, "test": {}}

        for split in splits:
            img_split_dir = self.images_dir / split
            lbl_split_dir = self.labels_dir / split

            if not img_split_dir.exists():
                report["errors"].append(f"Missing images directory: {img_split_dir}")
                report["is_valid"] = False
                continue
            if not lbl_split_dir.exists():
                report["errors"].append(f"Missing labels directory: {lbl_split_dir}")
                report["is_valid"] = False
                continue

            images = {f.stem: f for f in img_split_dir.glob("*.*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
            labels = {f.stem: f for f in lbl_split_dir.glob("*.txt")}

            # Check unaligned files
            missing_labels = [name for name in images if name not in labels]
            missing_images = [name for name in labels if name not in images]

            if missing_labels:
                report["warnings"].append(f"[{split}] {len(missing_labels)} images have no corresponding label file (background images)")
            if missing_images:
                report["errors"].append(f"[{split}] {len(missing_images)} label files have no corresponding image file")
                report["is_valid"] = False

            # Compute image hashes for leakage detection
            for stem, img_path in images.items():
                h = self._file_hash(img_path)
                split_hashes[split][h] = img_path

            # Count instances and validate label coordinates
            class_counts = Counter()
            instances = 0
            invalid_coords = 0

            for lbl_path in labels.values():
                content = lbl_path.read_text(encoding="utf-8", errors="ignore").strip()
                if not content:
                    continue
                for line in content.splitlines():
                    parts = line.strip().split()
                    if not parts:
                        continue
                    try:
                        cls_id = int(parts[0])
                        class_counts[cls_id] += 1
                        report["detected_classes"][cls_id] += 1
                        instances += 1
                        # Verify normalized coordinates
                        coords = [float(x) for x in parts[1:]]
                        for c in coords:
                            if c < -0.01 or c > 1.01:
                                invalid_coords += 1
                    except ValueError:
                        report["errors"].append(f"Corrupted label syntax in {lbl_path}")
                        report["is_valid"] = False

            report["splits"][split] = {
                "image_count": len(images),
                "label_count": len(labels),
                "instance_count": instances,
                "class_distribution": dict(class_counts),
                "missing_labels_count": len(missing_labels),
                "missing_images_count": len(missing_images),
                "invalid_coords_count": invalid_coords,
            }
            report["total_images"] += len(images)
            report["total_instances"] += instances

        # 5. Check for Data Leakage between splits
        for s1, s2 in [("train", "val"), ("train", "test"), ("val", "test")]:
            overlap = set(split_hashes[s1].keys()) & set(split_hashes[s2].keys())
            if overlap:
                report["data_leakage_detected"] = True
                report["is_valid"] = False
                for h in overlap:
                    detail = f"Duplicate image leaked between {s1} ({split_hashes[s1][h].name}) and {s2} ({split_hashes[s2][h].name})"
                    report["leakage_details"].append(detail)
                    report["errors"].append(detail)

        # 6. Check active vs declared classes
        detected_ids = set(report["detected_classes"].keys())
        declared_ids = set(FULL_CLASSES.keys())
        missing_classes = declared_ids - detected_ids
        if missing_classes:
            missing_names = [f"{cid}:{FULL_CLASSES[cid]}" for cid in sorted(missing_classes)]
            report["warnings"].append(
                f"Dataset contains annotations for {len(detected_ids)} of {len(declared_ids)} declared classes. "
                f"Missing classes in dataset: {', '.join(missing_names)}"
            )

        return report
