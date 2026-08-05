"""
============================================================
Road AI - Unified Segmentation Dataset Preparation
============================================================
Combines ALL downloaded datasets into ONE unified dataset
with YOLO segmentation format (polygon labels).

Input formats handled:
  - YOLO polygon (already correct)
  - YOLO bbox (converted to rectangular polygon)
  - Pascal VOC XML (converted to polygon)
  - COCO JSON (converted to polygon)
  - Folder-sorted classification (converted to full-image polygon)

Output format:
  unified/
    images/train/  images/val/  images/test/
    labels/train/  labels/val/  labels/test/
  
  Labels: class_id x1 y1 x2 y2 x3 y3 x4 y4 (polygon, normalized)
============================================================
"""

import os
import shutil
import random
import glob
import yaml
import json
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET

# ===================== CONFIGURATION =====================

ROOT = "D:/Road_AI_Project/ai_models"
DATASET_DIR = os.path.join(ROOT, "dataset")
UNIFIED_DIR = os.path.join(DATASET_DIR, "unified")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")

# Load config
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

CLASS_NAMES = config['names']  # {0: 'Pothole', 1: 'Edge_Deterioration', ...}

# Reverse mapping: name -> id (flexible matching)
NAME_TO_ID = {}
for cid, cname in CLASS_NAMES.items():
    NAME_TO_ID[cname.lower()] = cid
    NAME_TO_ID[cname.lower().replace("_", " ")] = cid
    NAME_TO_ID[cname.lower().replace("_", "")] = cid

# Aliases from various datasets
ALIASES = {
    # Potholes
    "pothole": 0, "road-pothole": 0, "potholes": 0,
    # Edge Deterioration
    "edge crack": 1, "edge cracks": 1, "edge cracking": 1, "edge deterioration": 1,
    # Alligator Cracking
    "alligator crack": 2, "alligator cracking": 2, "alligator_crack": 2,
    "d20": 2, "d21": 2,
    # Rutting
    "rutting": 3, "rut": 3,
    # Subsidence
    "subsidence": 4, "depression": 4, "depressions": 4,
    # Cracking
    "crack": 5, "cracks": 5, "cracking": 5,
    "longitudinal crack": 5, "longitudinal cracking": 5, "longitudinal (linear) cracking": 5,
    "transverse crack": 5, "transverse cracking": 5,
    "lateral crack": 5, "block crack": 5,
    "d00": 5, "d01": 5, "d10": 5, "d11": 5,
    # Bleeding
    "bleeding": 6, "fatty surface": 6,
    # Fretting / Ravelling
    "fretting": 7, "raveling": 7, "ravelling": 7, "raveling ": 7,
    # Repaired Pothole
    "repaired pothole": 8, "repaired": 8, "patch": 8, "patching": 8, "repair": 8,
    # Line Marking
    "line marking": 9, "road marking": 9, "lane marking": 9,
    "white line": 9, "yellow line": 9, "zebra": 9, "arrow": 9, "marking": 9,
    "bus lane": 9, "yellow markings": 9, "line 1": 9, "line 2": 9,
    "crossing": 9, "romb": 9, "slow": 9,
    "left arrow": 9, "forward arrow": 9, "forward arrow -left": 9,
    "forward arrow -right": 9, "right arrow": 9, "bicycle": 9,
    # Storm Drain  
    "storm drain": 10, "drain": 10, "storm_drain": 10,
    # Manhole
    "manhole": 11, "manhole cover": 11, "open_manhole": 11, "open-manhole": 11,
    # Guard Rail
    "guard rail": 12, "guardrail": 12, "barrier": 12, "guard_rail": 12,
    # Traffic Sign
    "traffic sign": 13, "sign": 13, "traffic_sign": 13,
    "trafficlight": 13, "speedlimit": 13, "crosswalk": 13,
    "stop": 13, "speed sign": 13,
    "green light": 13, "red light": 13,
    "speed limit 10": 13, "speed limit 20": 13, "speed limit 30": 13,
    "speed limit 40": 13, "speed limit 50": 13, "speed limit 60": 13,
    "speed limit 70": 13, "speed limit 80": 13, "speed limit 90": 13,
    "speed limit 100": 13, "speed limit 110": 13, "speed limit 120": 13,
    # Surface defects -> Cracking (general)
    "surface defects": 5, "surface_defects": 5,
    # Speed bumps
    "marked_speedbump": 13, "unpaved_road": 5,
}

for alias, cid in ALIASES.items():
    NAME_TO_ID[alias] = cid

TRAIN_RATIO = 0.80
VAL_RATIO = 0.15
TEST_RATIO = 0.05


# ===================== HELPERS =====================

def get_class_id(label_text):
    """Map label string to class ID."""
    label = label_text.strip().lower()
    if label in NAME_TO_ID:
        return NAME_TO_ID[label]
    # Partial match
    for key, val in NAME_TO_ID.items():
        if key in label or label in key:
            return val
    return None


def bbox_to_polygon(x_center, y_center, w, h):
    """Convert bbox (normalized) to polygon points (4 corners)."""
    x1 = max(0, x_center - w/2)
    y1 = max(0, y_center - h/2)
    x2 = min(1, x_center + w/2)
    y2 = min(1, y_center + h/2)
    # 4 corners: top-left, top-right, bottom-right, bottom-left
    return f"{x1:.6f} {y1:.6f} {x2:.6f} {y1:.6f} {x2:.6f} {y2:.6f} {x1:.6f} {y2:.6f}"


def create_dirs():
    """Create unified directory structure."""
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(UNIFIED_DIR, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(UNIFIED_DIR, 'labels', split), exist_ok=True)
    print("[OK] Created unified directory structure")


# ===================== DATASET PROCESSORS =====================

def process_yolo_seg(dataset_path, prefix):
    """Process YOLO format with polygon labels (>5 values per line)."""
    collected = []
    
    # Load class remapping from data.yaml
    remap = {}
    data_yaml = None
    for dy in Path(dataset_path).rglob('data.yaml'):
        data_yaml = dy
        break
    
    if data_yaml:
        with open(data_yaml) as f:
            dy = yaml.safe_load(f)
        names = dy.get('names', {})
        if isinstance(names, list):
            names = {i: n for i, n in enumerate(names)}
        for orig_id, name in names.items():
            new_id = get_class_id(name)
            if new_id is not None:
                remap[int(orig_id)] = new_id
    
    for split in ['train', 'valid', 'val', 'test']:
        img_dir = None
        lbl_dir = None
        
        # Try different structures
        for candidate in [
            (os.path.join(dataset_path, split, 'images'), os.path.join(dataset_path, split, 'labels')),
            (os.path.join(dataset_path, 'dataset', split, 'images'), os.path.join(dataset_path, 'dataset', split, 'labels')),
        ]:
            if os.path.exists(candidate[0]):
                img_dir, lbl_dir = candidate
                break
        
        if not img_dir or not os.path.exists(img_dir):
            continue
        
        for img_file in glob.glob(os.path.join(img_dir, '*.*')):
            ext = os.path.splitext(img_file)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.bmp']:
                continue
            
            base = os.path.splitext(os.path.basename(img_file))[0]
            lbl_file = os.path.join(lbl_dir, f"{base}.txt")
            
            if not os.path.exists(lbl_file):
                continue
            
            content = open(lbl_file, errors='ignore').read().strip()
            if not content:
                continue
            
            remapped_lines = []
            for line in content.split('\n'):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                orig_id = int(parts[0])
                new_id = remap.get(orig_id, orig_id)
                
                if len(parts) > 5:
                    # Already polygon format
                    remapped_lines.append(f"{new_id} {' '.join(parts[1:])}")
                else:
                    # Bbox format -> convert to polygon
                    x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    poly = bbox_to_polygon(x, y, w, h)
                    remapped_lines.append(f"{new_id} {poly}")
            
            if remapped_lines:
                collected.append({
                    'image': img_file,
                    'labels': remapped_lines,
                    'prefix': prefix
                })
    
    return collected


def process_yolo_roboflow(dataset_path, prefix):
    """Process Roboflow YOLO format (with car/ or proj/ or archive/ subfolder)."""
    collected = []
    
    # Find the actual root with data.yaml
    for dy in Path(dataset_path).rglob('data.yaml'):
        actual_root = dy.parent
        result = process_yolo_seg(str(actual_root), prefix)
        collected.extend(result)
        break
    
    if not collected:
        # Try direct
        collected = process_yolo_seg(dataset_path, prefix)
    
    return collected


def process_voc_xml(dataset_path, prefix):
    """Process Pascal VOC XML annotations."""
    collected = []
    
    xml_files = list(Path(dataset_path).rglob('*.xml'))
    
    for xml_file in xml_files:
        try:
            tree = ET.parse(str(xml_file))
            root = tree.getroot()
        except:
            continue
        
        # Find corresponding image
        base = xml_file.stem
        img_file = None
        for ext in ['.jpg', '.jpeg', '.png']:
            for candidate_dir in [
                xml_file.parent,
                xml_file.parent / 'images',
                xml_file.parent.parent / 'images',
                Path(str(xml_file.parent).replace('annotations', 'images')),
            ]:
                candidate = candidate_dir / f"{base}{ext}"
                if candidate.exists():
                    img_file = str(candidate)
                    break
            if img_file:
                break
        
        if not img_file:
            continue
        
        try:
            with Image.open(img_file) as img:
                img_w, img_h = img.size
        except:
            continue
        
        lines = []
        for obj in root.findall('object'):
            name_elem = obj.find('name')
            if name_elem is None:
                continue
            class_id = get_class_id(name_elem.text)
            if class_id is None:
                continue
            
            bbox = obj.find('bndbox')
            if bbox is None:
                continue
            
            xmin = float(bbox.find('xmin').text) / img_w
            ymin = float(bbox.find('ymin').text) / img_h
            xmax = float(bbox.find('xmax').text) / img_w
            ymax = float(bbox.find('ymax').text) / img_h
            
            xmin = max(0, min(1, xmin))
            ymin = max(0, min(1, ymin))
            xmax = max(0, min(1, xmax))
            ymax = max(0, min(1, ymax))
            
            # Convert to polygon (4 corners)
            poly = f"{xmin:.6f} {ymin:.6f} {xmax:.6f} {ymin:.6f} {xmax:.6f} {ymax:.6f} {xmin:.6f} {ymax:.6f}"
            lines.append(f"{class_id} {poly}")
        
        if lines:
            collected.append({
                'image': img_file,
                'labels': lines,
                'prefix': prefix
            })
    
    return collected


def process_coco_json(dataset_path, prefix):
    """Process COCO JSON annotations."""
    collected = []
    
    for json_file in Path(dataset_path).rglob('*.json'):
        try:
            with open(json_file) as f:
                coco = json.load(f)
        except:
            continue
        
        if 'categories' not in coco or 'annotations' not in coco:
            continue
        
        # Build category mapping
        cat_map = {}
        for cat in coco['categories']:
            cid = get_class_id(cat['name'])
            if cid is not None:
                cat_map[cat['id']] = cid
        
        # Build image lookup
        img_lookup = {}
        for img in coco.get('images', []):
            img_lookup[img['id']] = img
        
        # Group annotations by image
        ann_by_img = {}
        for ann in coco['annotations']:
            img_id = ann['image_id']
            cat_id = ann['category_id']
            if cat_id not in cat_map:
                continue
            
            if img_id not in ann_by_img:
                ann_by_img[img_id] = []
            
            img_info = img_lookup.get(img_id, {})
            w = img_info.get('width', 1)
            h = img_info.get('height', 1)
            
            bbox = ann['bbox']  # [x, y, width, height]
            x1 = bbox[0] / w
            y1 = bbox[1] / h
            x2 = (bbox[0] + bbox[2]) / w
            y2 = (bbox[1] + bbox[3]) / h
            
            x1 = max(0, min(1, x1))
            y1 = max(0, min(1, y1))
            x2 = max(0, min(1, x2))
            y2 = max(0, min(1, y2))
            
            poly = f"{x1:.6f} {y1:.6f} {x2:.6f} {y1:.6f} {x2:.6f} {y2:.6f} {x1:.6f} {y2:.6f}"
            ann_by_img[img_id].append(f"{cat_map[cat_id]} {poly}")
        
        # Find images
        img_base = json_file.parent
        for img_id, lines in ann_by_img.items():
            img_info = img_lookup.get(img_id, {})
            fname = img_info.get('file_name', '')
            
            img_path = None
            for search_dir in [img_base, img_base / 'images', img_base / 'train',
                             img_base / 'val', img_base.parent / 'images']:
                candidate = search_dir / fname
                if candidate.exists():
                    img_path = str(candidate)
                    break
            
            if img_path and lines:
                collected.append({
                    'image': img_path,
                    'labels': lines,
                    'prefix': prefix
                })
    
    return collected


def process_classification_folders(dataset_path, prefix, class_map):
    """Process folder-sorted classification dataset (whole-image label)."""
    collected = []
    
    for class_name, class_folder in class_map.items():
        class_id = get_class_id(class_name)
        if class_id is None:
            print(f"    [WARN] Unknown class: {class_name}")
            continue
        
        folder_path = os.path.join(dataset_path, class_folder)
        if not os.path.exists(folder_path):
            continue
        
        for img_file in glob.glob(os.path.join(folder_path, '**', '*.*'), recursive=True):
            ext = os.path.splitext(img_file)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.bmp']:
                continue
            
            # Use 80% of image as the defect region (centered)
            margin = 0.1
            poly = f"{margin:.6f} {margin:.6f} {1-margin:.6f} {margin:.6f} {1-margin:.6f} {1-margin:.6f} {margin:.6f} {1-margin:.6f}"
            
            collected.append({
                'image': img_file,
                'labels': [f"{class_id} {poly}"],
                'prefix': prefix
            })
    
    return collected


# ===================== MAIN =====================

def main():
    print("=" * 60)
    print("  Road AI - Unified Segmentation Dataset Preparation")
    print("  Converting ALL formats to YOLO-seg polygon labels")
    print("=" * 60)
    
    # Clean previous unified data
    if os.path.exists(UNIFIED_DIR):
        shutil.rmtree(UNIFIED_DIR)
    create_dirs()
    
    all_items = []
    class_counts = {}
    
    # === 1. YOLO POLYGON DATASETS (best quality) ===
    print("\n--- [1/7] YOLO Polygon Datasets ---")
    
    for name, path_suffix in [
        ("seg_pot1", "Seg_Pothole_1"),
        ("pot_seg", "pothole-seg-kaggle/Pothole_Segmentation_YOLOv8"),
        ("pot_poly", "archive_(1)/dataset"),
    ]:
        ds_path = os.path.join(DATASET_DIR, path_suffix)
        if os.path.exists(ds_path):
            items = process_yolo_seg(ds_path, name)
            print(f"  {name}: {len(items)} images (polygon)")
            all_items.extend(items)
    
    # === 2. YOLO BBOX DATASETS (convert to polygon) ===
    print("\n--- [2/7] YOLO BBox Datasets (converting to polygon) ---")
    
    for name, path_suffix in [
        ("pot_bbox", "archive_(5)"),
        ("man_bbox", "archive_(3)"),
    ]:
        ds_path = os.path.join(DATASET_DIR, path_suffix)
        if os.path.exists(ds_path):
            items = process_yolo_seg(ds_path, name)
            print(f"  {name}: {len(items)} images")
            all_items.extend(items)
    
    # === 3. ROBOFLOW YOLO DATASETS (may have subfolder) ===
    print("\n--- [3/7] Roboflow YOLO Datasets ---")
    
    for name, path_suffix in [
        ("road_dmg", "archive_(6)"),
        ("signs_rf", "archive"),
        ("lane_seg", "archive_(11)"),
    ]:
        ds_path = os.path.join(DATASET_DIR, path_suffix)
        if os.path.exists(ds_path):
            items = process_yolo_roboflow(ds_path, name)
            print(f"  {name}: {len(items)} images")
            all_items.extend(items)
    
    # === 4. VOC XML DATASETS ===
    print("\n--- [4/7] Pascal VOC XML Datasets ---")
    
    for name, path_suffix in [
        ("pot_xml", "annotated-potholes"),
        ("signs_xml", "road-signs-kaggle"),
    ]:
        ds_path = os.path.join(DATASET_DIR, path_suffix)
        if os.path.exists(ds_path):
            items = process_voc_xml(ds_path, name)
            print(f"  {name}: {len(items)} images")
            all_items.extend(items)
    
    # === 5. COCO JSON DATASETS ===
    print("\n--- [5/7] COCO JSON Datasets ---")
    
    for name, path_suffix in [
        ("pcm_coco", "pothole-crack-manhole-kaggle"),
    ]:
        ds_path = os.path.join(DATASET_DIR, path_suffix)
        if os.path.exists(ds_path):
            items = process_coco_json(ds_path, name)
            print(f"  {name}: {len(items)} images")
            all_items.extend(items)
    
    # === 6. CLASSIFICATION FOLDER DATASETS ===
    print("\n--- [6/7] Classification Folder Datasets ---")
    
    # archive_(7): Cracks, Patch, Potholes, Surface_Defects
    items = process_classification_folders(
        os.path.join(DATASET_DIR, "archive_(7)"),
        "defects",
        {
            "Cracks": "Cracks/Cracks",
            "Patch": "Patch/Patch",
            "Potholes": "Potholes/Potholes",
            "Surface_Defects": "Surface_Defects/Surface Defects",
        }
    )
    print(f"  archive_(7): {len(items)} images (Cracks, Patch, Potholes, Surface)")
    all_items.extend(items)
    
    # archive_(8): Multiple rare defect types
    items = process_classification_folders(
        os.path.join(DATASET_DIR, "archive_(8)/data/train"),
        "rare_train",
        {
            "Alligator Cracking": "Alligator Cracking",
            "Depressions": "Depressions",
            "Edge Cracks": "Edge Cracks",
            "Longitudinal (Linear) Cracking": "Longitudinal (Linear) Cracking",
            "Potholes": "Potholes",
            "Raveling": "Raveling",
            "Rutting": "Rutting",
        }
    )
    print(f"  archive_(8) train: {len(items)} images (rare defects)")
    all_items.extend(items)
    
    items = process_classification_folders(
        os.path.join(DATASET_DIR, "archive_(8)/data/test"),
        "rare_test",
        {
            "Alligator Cracking": "Alligator Cracking",
            "Depressions": "Depressions",
            "Edge Cracks": "Edge Cracks",
            "Longitudinal (Linear) Cracking": "Longitudinal (Linear) Cracking",
            "Potholes": "Potholes",
            "Raveling": "Raveling",
            "Rutting": "Rutting",
        }
    )
    print(f"  archive_(8) test: {len(items)} images")
    all_items.extend(items)
    
    # === 7. COUNT CLASS DISTRIBUTION ===
    print("\n--- [7/7] Analyzing Class Distribution ---")
    
    for item in all_items:
        for line in item['labels']:
            cid = int(line.split()[0])
            cname = CLASS_NAMES.get(cid, f"unknown_{cid}")
            class_counts[cname] = class_counts.get(cname, 0) + 1
    
    print(f"\n  Class Distribution:")
    for cid in sorted(CLASS_NAMES.keys()):
        cname = CLASS_NAMES[cid]
        count = class_counts.get(cname, 0)
        bar = '#' * min(50, count // 10)
        print(f"    {cid:2d}: {cname:<22s} {count:6d} {bar}")
    
    # === SPLIT AND COPY ===
    print(f"\n{'=' * 60}")
    print(f"  Total samples: {len(all_items)}")
    print(f"  Splitting into train/val/test...")
    print(f"{'=' * 60}")
    
    random.seed(42)
    random.shuffle(all_items)
    
    n = len(all_items)
    n_train = int(n * TRAIN_RATIO)
    n_val = int(n * VAL_RATIO)
    
    splits = {
        'train': all_items[:n_train],
        'val': all_items[n_train:n_train + n_val],
        'test': all_items[n_train + n_val:]
    }
    
    for split_name, items in splits.items():
        print(f"\n  [{split_name.upper()}] Copying {len(items)} images...")
        for i, item in enumerate(items):
            ext = os.path.splitext(item['image'])[1]
            new_name = f"{item['prefix']}_{i:06d}"
            
            # Copy image
            dst_img = os.path.join(UNIFIED_DIR, 'images', split_name, f"{new_name}{ext}")
            try:
                shutil.copy2(item['image'], dst_img)
            except Exception as e:
                continue
            
            # Write label (polygon format)
            dst_lbl = os.path.join(UNIFIED_DIR, 'labels', split_name, f"{new_name}.txt")
            with open(dst_lbl, 'w') as f:
                f.write('\n'.join(item['labels']))
    
    # === CREATE data.yaml FOR TRAINING ===
    data_yaml = {
        'path': UNIFIED_DIR.replace('\\', '/'),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': len(CLASS_NAMES),
        'names': CLASS_NAMES,
    }
    
    yaml_path = os.path.join(UNIFIED_DIR, 'data.yaml')
    with open(yaml_path, 'w') as f:
        yaml.dump(data_yaml, f, default_flow_style=False)
    
    # === FINAL SUMMARY ===
    print(f"\n{'=' * 60}")
    print(f"  DATASET PREPARED SUCCESSFULLY!")
    print(f"{'=' * 60}")
    print(f"  Train: {len(splits['train'])} images")
    print(f"  Val:   {len(splits['val'])} images")
    print(f"  Test:  {len(splits['test'])} images")
    print(f"  Total: {len(all_items)} images")
    print(f"  Path:  {UNIFIED_DIR}")
    print(f"  Config: {yaml_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
