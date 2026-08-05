"""
Road AI - Download Kaggle datasets only (reliable)
Roboflow API key has permission issues, so we use Kaggle.
"""
import os
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

SAVE_PATH = "D:/Road_AI_Project/ai_models/dataset"
os.makedirs(SAVE_PATH, exist_ok=True)

api = KaggleApi()
api.authenticate()
print("[OK] Kaggle API authenticated\n")

DATASETS = [
    ("farzadnekouei/pothole-image-segmentation-dataset", "pothole-seg-kaggle", "Pothole Segmentation masks"),
    ("chitholian/annotated-potholes-dataset", "annotated-potholes", "Annotated Potholes"),
    ("andrewmvd/road-damage-detection", "rdd-kaggle", "Road Damage Detection (cracks, potholes)"),
    ("andrewmvd/road-sign-detection", "road-signs-kaggle", "Traffic Signs"),
    ("sachinpatel21/pothole-image-dataset", "pothole-images-kaggle", "Pothole Images"),
    ("amerzish/road-defects-images", "road-defects-kaggle", "Road Defects mixed"),
    ("ayushchauhan009/raveling-detection-ce784a-2023", "ravelling-kaggle", "Ravelling/Fretting images"),
    ("sabidrahman/pothole-cracks-and-openmanhole", "pothole-crack-manhole-kaggle", "Potholes Cracks Manholes"),
    ("thendu3/road-lane-marking-signs", "lane-markings-kaggle", "Lane Markings & Signs"),
    ("theol369/road-damage-dataset-potholes-cracks-and-manholes", "road-damage-all-kaggle", "Road Damage comprehensive"),
    ("faridafzali/potholes-cracks-and-openmanholes-road-hazards", "road-hazards-kaggle", "Road Hazards"),
    ("programmerrdai/road-issues-detection-dataset", "road-issues-kaggle", "Road Issues Detection"),
]

for i, (slug, folder, desc) in enumerate(DATASETS, 1):
    target_dir = os.path.join(SAVE_PATH, folder)
    
    # Skip if already done
    if os.path.exists(target_dir):
        exts = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.xml", "*.txt"]
        count = sum(len(list(Path(target_dir).rglob(e))) for e in exts)
        if count > 10:
            print(f"[{i}/{len(DATASETS)}] [SKIP] {desc} -- already have {count} files")
            continue
    
    os.makedirs(target_dir, exist_ok=True)
    print(f"[{i}/{len(DATASETS)}] Downloading: {desc}")
    print(f"   Source: {slug}")
    
    try:
        api.dataset_download_files(slug, path=target_dir, unzip=True)
        exts = ["*.jpg", "*.jpeg", "*.png"]
        img_count = sum(len(list(Path(target_dir).rglob(e))) for e in exts)
        print(f"   [OK] {img_count} images\n")
    except Exception as e:
        if "403" in str(e):
            print(f"   [DENIED] Visit: https://www.kaggle.com/datasets/{slug}")
            print(f"   Accept terms on website, then re-run\n")
        else:
            print(f"   [FAILED] {e}\n")

# Summary
print("\n" + "=" * 60)
print("  DOWNLOAD COMPLETE -- Summary")
print("=" * 60)
total = 0
for slug, folder, desc in DATASETS:
    target = os.path.join(SAVE_PATH, folder)
    if os.path.exists(target):
        exts = ["*.jpg", "*.jpeg", "*.png"]
        count = sum(len(list(Path(target).rglob(e))) for e in exts)
        if count > 0:
            print(f"  {folder}: {count} images")
            total += count
print(f"\n  TOTAL: {total} images")
print(f"\n  Next: python prepare_dataset.py")
