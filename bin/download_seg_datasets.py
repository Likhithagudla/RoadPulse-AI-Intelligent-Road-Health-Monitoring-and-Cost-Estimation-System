"""
============================================================
Road AI - Segmentation Dataset Downloader v2
============================================================
Downloads segmentation datasets using direct Roboflow Universe
URLs (bypasses workspace permission issues).

Covers all 14 classes for YOLOv8-seg training.
============================================================
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from urllib.request import urlretrieve, urlopen
from urllib.error import URLError

SAVE_PATH = str(Path(__file__).resolve().parent.parent / "ai_models/dataset")
ROBOFLOW_API_KEY = "RPOBmjD1UhE2l7j05cCv"
os.makedirs(SAVE_PATH, exist_ok=True)


def download_from_roboflow_url(name, workspace, project, version, desc, covers, format_type="yolov8"):
    """Download a dataset using Roboflow Universe API URL."""
    target_dir = os.path.join(SAVE_PATH, name)
    
    # Skip if already downloaded
    if os.path.exists(target_dir):
        img_count = len(list(Path(target_dir).rglob("*.jpg"))) + \
                   len(list(Path(target_dir).rglob("*.png")))
        if img_count > 10:
            print(f"\n  [OK] [SKIP] {name} -- Already have {img_count} images")
            return True
    
    print(f"\n  [>>] [{name}]")
    print(f"     {desc}")
    print(f"     Covers: {', '.join(covers)}")
    
    try:
        from roboflow import Roboflow
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        project_obj = rf.workspace(workspace).project(project)
        dataset = project_obj.version(version).download(format_type, location=target_dir)
        
        img_count = len(list(Path(target_dir).rglob("*.jpg"))) + \
                   len(list(Path(target_dir).rglob("*.png")))
        
        # Check for polygon labels
        has_polygon = check_polygon_labels(target_dir)
        fmt = "POLYGON [OK]" if has_polygon else "BBOX [WARN]"
        print(f"     -> {img_count} images downloaded [{fmt}]")
        return True
        
    except Exception as e:
        print(f"     [FAILED] Roboflow: {e}")
        return False


def check_polygon_labels(dataset_dir):
    """Check if a dataset has polygon (segmentation) labels."""
    for lf in Path(dataset_dir).rglob("*.txt"):
        if lf.name in ["classes.txt", "README.txt", "data.yaml"]:
            continue
        try:
            content = lf.read_text().strip()
            if content:
                first_line = content.split('\n')[0].split()
                if len(first_line) > 5:
                    return True
        except:
            pass
    return False


def download_kaggle_dataset(slug, name, desc, folder, covers):
    """Download a dataset from Kaggle."""
    target_dir = os.path.join(SAVE_PATH, folder)
    
    if os.path.exists(target_dir):
        img_count = len(list(Path(target_dir).rglob("*.jpg"))) + \
                   len(list(Path(target_dir).rglob("*.png")))
        if img_count > 10:
            print(f"\n  [OK] [SKIP] {name} -- Already have {img_count} images")
            return True
    
    print(f"\n  [>>] [{name}]")
    print(f"     {desc}")
    print(f"     Covers: {', '.join(covers)}")
    
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(slug, path=target_dir, unzip=True)
        
        img_count = len(list(Path(target_dir).rglob("*.jpg"))) + \
                   len(list(Path(target_dir).rglob("*.png")))
        has_polygon = check_polygon_labels(target_dir)
        fmt = "POLYGON [OK]" if has_polygon else "IMAGES [OK]"
        print(f"     -> {img_count} images downloaded [{fmt}]")
        return True
        
    except Exception as e:
        if "403" in str(e):
            print(f"     [DENIED] Visit: https://www.kaggle.com/datasets/{slug}")
            print(f"        Accept terms, then re-run")
        else:
            print(f"     [FAILED] {e}")
        return False


def main():
    print("=" * 60)
    print("  Road AI -- Segmentation Dataset Downloader v2")
    print("  Covers ALL 14 classes (Defects + Infrastructure)")
    print("  Polygon mask annotations for YOLOv8-seg")
    print("=" * 60)
    
    results = {}
    
    # ================================================================
    # SECTION 1: ROBOFLOW DATASETS
    # ================================================================
    print("\n" + "=" * 60)
    print("  [SECTION 1] ROBOFLOW SEGMENTATION DATASETS")
    print("=" * 60)
    
    roboflow_datasets = [
        # Pothole segmentation
        ("Seg_Pothole_1", "project-road-damage", "yolo-v8-set", 1,
         "Potholes - 126 images, polygon masks",
         ["Pothole"]),
         
        # Potholes & Cracks
        ("Seg_Pothole_2", "test-grcx5", "road-potholes-and-cracks", 1,
         "Potholes & Cracks - 1581 images, polygon masks",
         ["Pothole", "Cracking"]),
        
        # Road Damage multi-class
        ("Seg_RoadDamage", "road-damage-segmentation-dclzx", "road-damage-segmentatation", 2,
         "Road Damage - 610 images, multiple defect polygons",
         ["Pothole", "Cracking", "Alligator_Cracking"]),
         
        # RDD Instance segmentation
        ("Seg_RDD", "rdd-instance", "road-damage-detection-qdrps", 1,
         "RDD Instance Seg - 1000 images",
         ["Pothole", "Cracking", "Alligator_Cracking"]),

        # Manhole
        ("Seg_Manhole", "manhole-drainage", "aggregate", 1,
         "Manholes & Drains - instance segmentation",
         ["Manhole"]),
    ]
    
    for name, ws, proj, ver, desc, covers in roboflow_datasets:
        ok = download_from_roboflow_url(name, ws, proj, ver, desc, covers)
        results[name] = ok
    
    # ================================================================
    # SECTION 2: KAGGLE DATASETS (work more reliably)
    # ================================================================
    print("\n" + "=" * 60)
    print("  [SECTION 2] KAGGLE SEGMENTATION DATASETS")
    print("=" * 60)
    
    kaggle_datasets = [
        # Pothole segmentation
        ("farzadnekouei/pothole-image-segmentation-dataset",
         "Pothole Segmentation", "Pothole masks for YOLOv8-seg",
         "pothole-seg-kaggle", ["Pothole"]),
         
        # Road damage with annotations
        ("chitholian/annotated-potholes-dataset",
         "Annotated Potholes", "Potholes with polygon annotations",
         "annotated-potholes", ["Pothole"]),

        # Road damage detection
        ("andrewmvd/road-damage-detection",
         "RDD Original", "Road Damage Detection - cracks, potholes",
         "rdd-kaggle", ["Cracking", "Pothole", "Alligator_Cracking"]),
         
        # Road sign detection
        ("andrewmvd/road-sign-detection",
         "Road Sign Detection", "Traffic signs - various types",
         "road-signs-kaggle", ["Traffic_Sign"]),

        # Pothole image dataset
        ("sachinpatel21/pothole-image-dataset",
         "Pothole Images", "Large pothole image collection",
         "pothole-images-kaggle", ["Pothole"]),
         
        # Road defects
        ("amerzish/road-defects-images",
         "Road Defects", "Mixed road defect images",
         "road-defects-kaggle", ["Cracking", "Pothole", "Edge_Deterioration"]),
         
        # Ravelling
        ("ayushchauhan009/raveling-detection-ce784a-2023",
         "Ravelling Detection", "Ravelling/fretting images",
         "ravelling-kaggle", ["Fretting"]),
         
        # Potholes cracks manholes
        ("sabidrahman/pothole-cracks-and-openmanhole",
         "Potholes Cracks Manholes", "Multi-class detection",
         "pothole-crack-manhole-kaggle", ["Pothole", "Cracking", "Manhole"]),
         
        # Road lane markings
        ("thendu3/road-lane-marking-signs",
         "Lane Markings & Signs", "Road lane lines and signs",
         "lane-markings-kaggle", ["Line_Marking", "Traffic_Sign"]),
    ]
    
    for slug, name, desc, folder, covers in kaggle_datasets:
        ok = download_kaggle_dataset(slug, name, desc, folder, covers)
        results[folder] = ok
    
    # ================================================================
    # SECTION 3: VERIFICATION
    # ================================================================
    print("\n" + "=" * 60)
    print("  DATASET VERIFICATION & CLASS COVERAGE")
    print("=" * 60)
    
    ALL_CLASSES = {
        0: "Pothole", 1: "Edge_Deterioration", 2: "Alligator_Cracking",
        3: "Rutting", 4: "Subsidence", 5: "Cracking", 6: "Bleeding",
        7: "Fretting", 8: "Repaired_Pothole",
        9: "Line_Marking", 10: "Storm_Drain", 11: "Manhole",
        12: "Guard_Rail", 13: "Traffic_Sign",
    }
    
    total_images = 0
    total_polygon = 0
    total_bbox = 0
    
    for ds_name in sorted(os.listdir(SAVE_PATH)):
        ds_path = os.path.join(SAVE_PATH, ds_name)
        if not os.path.isdir(ds_path):
            continue
        
        img_exts = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
        img_count = sum(len(list(Path(ds_path).rglob(ext))) for ext in img_exts)
        
        if img_count == 0:
            continue
        
        polygon_count = 0
        bbox_count = 0
        for lf in Path(ds_path).rglob("*.txt"):
            if lf.name in ["classes.txt", "README.txt", "notes.txt", "README.roboflow.txt"]:
                continue
            try:
                content = lf.read_text(errors='ignore').strip()
                if not content:
                    continue
                first_line = content.split('\n')[0].split()
                if len(first_line) > 5:
                    polygon_count += 1
                elif len(first_line) == 5:
                    bbox_count += 1
            except:
                pass
        
        label_type = "[POLYGON]" if polygon_count > bbox_count else \
                     "[BBOX]" if bbox_count > 0 else "[IMAGES ONLY]"
        
        print(f"\n  {ds_name}:")
        print(f"    Images: {img_count} | Labels: {polygon_count} poly, {bbox_count} bbox -> {label_type}")
        
        total_images += img_count
        total_polygon += polygon_count
        total_bbox += bbox_count
    
    print(f"\n{'=' * 60}")
    print(f"  TOTALS")
    print(f"{'=' * 60}")
    print(f"  Total images:      {total_images}")
    print(f"  Polygon labels:    {total_polygon}")
    print(f"  BBox labels:       {total_bbox}")
    
    success_count = sum(1 for v in results.values() if v)
    fail_count = sum(1 for v in results.values() if not v)
    print(f"  Downloads:         {success_count} OK, {fail_count} failed")
    
    print(f"\n{'=' * 60}")
    print(f"  NEXT STEPS")
    print(f"{'=' * 60}")
    print(f"  1. Run: python prepare_dataset.py  (unify all datasets)")
    print(f"  2. Run: python train_model.py --mode train  (train model)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
