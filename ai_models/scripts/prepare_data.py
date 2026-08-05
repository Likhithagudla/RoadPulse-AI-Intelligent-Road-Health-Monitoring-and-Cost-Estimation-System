"""
RoadPulse AI - Step 3: Prepare Dataset for YOLOv8 Training
Converts VOC XML annotations to YOLO format and splits into train/val/test.
"""
import os
import sys
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# ── Configuration ──────────────────────────────────────
DATASET_DIR = Path("D:/Road_AI_Project/ai_models/dataset")
OUTPUT_DIR = Path("D:/Road_AI_Project/ai_models/dataset/unified")

# Our class mapping - class_id: class_name
# For now we use what we have in the data. We can add more classes later.
CLASS_MAP = {
    "pothole": 0,
    "potholes": 0,    # alternate spelling
    "crack": 1,
    "cracking": 1,
    "alligator_cracking": 1,
    "d00": 1,         # RDD format for cracking
    "d10": 1,         # RDD format for cracking
    "d20": 2,         # RDD format for other damage
    "d40": 0,         # RDD format for pothole
    "d43": 0,         # RDD format for pothole
    "d44": 0,         # RDD format for pothole
}

# Class names list (index = class_id)
CLASS_NAMES = ["pothole", "cracking", "road_damage"]

# Split ratios
TRAIN_RATIO = 0.80
VAL_RATIO = 0.15
TEST_RATIO = 0.05

RANDOM_SEED = 42


def voc_to_yolo(xml_path, img_width, img_height):
    """Convert a single VOC XML annotation to YOLO format lines."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        return []

    # Get image size from XML if available
    size = root.find('size')
    if size is not None:
        w = int(size.find('width').text)
        h = int(size.find('height').text)
        if w > 0 and h > 0:
            img_width, img_height = w, h

    yolo_lines = []
    for obj in root.findall('object'):
        name = obj.find('name').text.strip().lower()

        # Map class name
        class_id = CLASS_MAP.get(name, None)
        if class_id is None:
            # Try partial match
            for key, cid in CLASS_MAP.items():
                if key in name or name in key:
                    class_id = cid
                    break

        if class_id is None:
            # Unknown class - default to road_damage (class 2)
            class_id = 2

        bbox = obj.find('bndbox')
        xmin = float(bbox.find('xmin').text)
        ymin = float(bbox.find('ymin').text)
        xmax = float(bbox.find('xmax').text)
        ymax = float(bbox.find('ymax').text)

        # Clamp to image bounds
        xmin = max(0, min(xmin, img_width))
        ymin = max(0, min(ymin, img_height))
        xmax = max(0, min(xmax, img_width))
        ymax = max(0, min(ymax, img_height))

        # Skip invalid boxes
        if xmax <= xmin or ymax <= ymin:
            continue

        # Convert to YOLO format: x_center, y_center, width, height (normalized 0-1)
        x_center = ((xmin + xmax) / 2.0) / img_width
        y_center = ((ymin + ymax) / 2.0) / img_height
        width = (xmax - xmin) / img_width
        height = (ymax - ymin) / img_height

        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

    return yolo_lines


def process_annotated_potholes():
    """Process the annotated-potholes-dataset (VOC XML format)."""
    src_dir = DATASET_DIR / "annotated-potholes-dataset" / "annotated-images"

    if not src_dir.exists():
        print("  [SKIP] annotated-potholes-dataset not found")
        return []

    pairs = []
    xml_files = sorted(src_dir.glob("*.xml"))
    print(f"  Found {len(xml_files)} XML annotation files")

    for xml_path in xml_files:
        img_name = xml_path.stem + ".jpg"
        img_path = src_dir / img_name

        if not img_path.exists():
            # Try PNG
            img_name = xml_path.stem + ".png"
            img_path = src_dir / img_name

        if not img_path.exists():
            continue

        yolo_lines = voc_to_yolo(xml_path, 640, 640)
        if yolo_lines:
            pairs.append((img_path, yolo_lines))

    print(f"  Converted {len(pairs)} images with valid annotations")
    return pairs


def process_pothole_images():
    """Process pothole-image-dataset (classification only, no bounding boxes).
    We skip these for object detection training since they lack annotations.
    But we log how many are available for future use."""
    src_dir = DATASET_DIR / "pothole-image-dataset" / "pothole_image_data" / "Pothole_Image_Data"

    if not src_dir.exists():
        print("  [SKIP] pothole-image-dataset not found")
        return

    img_count = len(list(src_dir.glob("*.jpg")))
    print(f"  Found {img_count} pothole images (NO annotations - skipped for training)")
    print(f"  TIP: These can be used later for classification or self-training")


def create_yolo_dataset(pairs):
    """Create the YOLO dataset directory structure with train/val/test splits."""

    # Shuffle and split
    random.seed(RANDOM_SEED)
    random.shuffle(pairs)

    n_total = len(pairs)
    n_train = int(n_total * TRAIN_RATIO)
    n_val = int(n_total * VAL_RATIO)

    train_pairs = pairs[:n_train]
    val_pairs = pairs[n_train:n_train + n_val]
    test_pairs = pairs[n_train + n_val:]

    print(f"\n  Split: {len(train_pairs)} train / {len(val_pairs)} val / {len(test_pairs)} test")

    # Create directory structure
    for split in ['train', 'val', 'test']:
        (OUTPUT_DIR / split / 'images').mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / split / 'labels').mkdir(parents=True, exist_ok=True)

    # Copy files
    splits = [('train', train_pairs), ('val', val_pairs), ('test', test_pairs)]
    total_annotations = 0

    for split_name, split_pairs in splits:
        count = 0
        for img_path, yolo_lines in split_pairs:
            # Copy image
            dst_img = OUTPUT_DIR / split_name / 'images' / img_path.name
            shutil.copy2(img_path, dst_img)

            # Write YOLO label file
            label_name = img_path.stem + '.txt'
            dst_label = OUTPUT_DIR / split_name / 'labels' / label_name
            with open(dst_label, 'w') as f:
                f.write('\n'.join(yolo_lines))

            count += 1
            total_annotations += len(yolo_lines)

        print(f"  {split_name}: {count} images copied")

    return total_annotations


def create_data_yaml():
    """Create the data.yaml file for YOLOv8 training."""
    yaml_content = f"""# RoadPulse AI - YOLOv8 Dataset Configuration
# Auto-generated by prepare_dataset.py

path: {OUTPUT_DIR.as_posix()}
train: train/images
val: val/images
test: test/images

# Number of classes
nc: {len(CLASS_NAMES)}

# Class names
names: {CLASS_NAMES}
"""

    yaml_path = OUTPUT_DIR / "data.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"\n  data.yaml saved to: {yaml_path}")
    return yaml_path


def verify_dataset():
    """Verify the created dataset."""
    print("\n  VERIFICATION:")
    for split in ['train', 'val', 'test']:
        img_dir = OUTPUT_DIR / split / 'images'
        lbl_dir = OUTPUT_DIR / split / 'labels'

        n_imgs = len(list(img_dir.glob("*.*"))) if img_dir.exists() else 0
        n_lbls = len(list(lbl_dir.glob("*.txt"))) if lbl_dir.exists() else 0

        status = "OK" if n_imgs == n_lbls and n_imgs > 0 else "MISMATCH!"
        print(f"    {split}: {n_imgs} images, {n_lbls} labels [{status}]")

    # Count total annotations per class
    class_counts = {name: 0 for name in CLASS_NAMES}
    for split in ['train', 'val', 'test']:
        lbl_dir = OUTPUT_DIR / split / 'labels'
        if not lbl_dir.exists():
            continue
        for lbl_file in lbl_dir.glob("*.txt"):
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cls_id = int(parts[0])
                        if cls_id < len(CLASS_NAMES):
                            class_counts[CLASS_NAMES[cls_id]] += 1

    print(f"\n  ANNOTATIONS PER CLASS:")
    for name, count in class_counts.items():
        bar = "#" * min(count // 5, 40)
        print(f"    {name:20s}: {count:5d} {bar}")


def main():
    print("=" * 60)
    print("  RoadPulse AI - Dataset Preparation (Step 3)")
    print("=" * 60)

    # Clean previous output
    if OUTPUT_DIR.exists():
        print(f"\n  Cleaning previous dataset at {OUTPUT_DIR}...")
        shutil.rmtree(OUTPUT_DIR)

    print(f"\n[1] Processing Annotated Potholes Dataset...")
    all_pairs = process_annotated_potholes()

    print(f"\n[2] Checking Pothole Image Dataset...")
    process_pothole_images()

    if not all_pairs:
        print("\n  ERROR: No annotated data found! Cannot create training dataset.")
        sys.exit(1)

    print(f"\n[3] Creating YOLO dataset structure...")
    total_annotations = create_yolo_dataset(all_pairs)

    print(f"\n[4] Creating data.yaml config...")
    yaml_path = create_data_yaml()

    print(f"\n[5] Verifying dataset...")
    verify_dataset()

    # Final summary
    print("\n" + "=" * 60)
    print("  DATASET PREPARATION COMPLETE!")
    print("=" * 60)
    print(f"  Total images with annotations: {len(all_pairs)}")
    print(f"  Total bounding box annotations: {total_annotations}")
    print(f"  Classes: {CLASS_NAMES}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  Config file: {yaml_path}")
    print()
    print("  Next step: Train the model with:")
    print("    python train_yolo.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
