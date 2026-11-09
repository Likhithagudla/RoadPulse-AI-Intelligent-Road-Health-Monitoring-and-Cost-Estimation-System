"""
RoadPulse AI - Dataset Downloader
Downloads road damage datasets from Kaggle for model training.
"""
import os
import sys
import zipfile
import shutil
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
BASE_DIR = Path(str(Path(__file__).resolve().parent.parent / "ai_models/dataset"))

# ── Kaggle Datasets to Download ─────────────────────────
# These are the best free road damage datasets on Kaggle
DATASETS = [
    {
        "slug": "sachinpatel21/pothole-image-dataset",
        "name": "Pothole Image Dataset",
        "folder": "pothole-image-dataset",
    },
    {
        "slug": "chitholian/annotated-potholes-dataset",
        "name": "Annotated Potholes Dataset",
        "folder": "annotated-potholes-dataset",
    },
    {
        "slug": "andrewmvd/road-damage-detection",
        "name": "Road Damage Detection (RDD)",
        "folder": "road-damage-detection",
    },
]


def download_dataset(api, slug, folder):
    """Download a single dataset from Kaggle."""
    dest = BASE_DIR / folder
    
    if dest.exists() and any(dest.iterdir()):
        # Check if it has actual image files (not just empty dirs)
        img_count = len(list(dest.rglob("*.jpg"))) + len(list(dest.rglob("*.png")))
        if img_count > 0:
            print(f"  ✓ Already downloaded ({img_count} images found)")
            return True
    
    dest.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"  Downloading from Kaggle...")
        api.dataset_download_files(slug, path=str(dest), unzip=True)
        
        # Count what we got
        img_count = len(list(dest.rglob("*.jpg"))) + len(list(dest.rglob("*.png")))
        print(f"  ✓ Downloaded successfully! ({img_count} images)")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            print(f"  ✗ Access denied (403)")
            print(f"    → You need to accept the dataset rules on Kaggle first.")
            print(f"    → Visit: https://www.kaggle.com/datasets/{slug}")
            print(f"    → Click the 'Download' button once on the website to accept terms.")
        elif "404" in error_msg:
            print(f"  ✗ Dataset not found (404) - slug may have changed")
        else:
            print(f"  ✗ Error: {error_msg}")
        return False


def main():
    print("=" * 60)
    print("  RoadPulse AI — Dataset Downloader")
    print("=" * 60)
    print()
    
    # Setup Kaggle API
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        print("✓ Kaggle API authenticated successfully")
        print()
    except Exception as e:
        print("✗ Kaggle API authentication failed!")
        print(f"  Error: {e}")
        print()
        print("  To fix this:")
        print("  1. Go to https://www.kaggle.com/settings")
        print("  2. Scroll to 'API' section")
        print("  3. Click 'Create New Token'")
        print("  4. Save the downloaded kaggle.json to:")
        print(f"     {Path.home() / '.kaggle' / 'kaggle.json'}")
        sys.exit(1)
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download each dataset
    results = []
    for i, ds in enumerate(DATASETS, 1):
        print(f"[{i}/{len(DATASETS)}] {ds['name']}")
        print(f"    Source: kaggle.com/datasets/{ds['slug']}")
        success = download_dataset(api, ds["slug"], ds["folder"])
        results.append((ds["name"], success))
        print()
    
    # Summary
    print("=" * 60)
    print("  DOWNLOAD SUMMARY")
    print("=" * 60)
    
    total_images = 0
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    # Count all images across all dataset folders
    for folder in BASE_DIR.iterdir():
        if folder.is_dir():
            count = len(list(folder.rglob("*.jpg"))) + len(list(folder.rglob("*.png")))
            if count > 0:
                total_images += count
                print(f"    └─ {folder.name}: {count} images")
    
    print()
    print(f"  Total images available: {total_images}")
    
    if total_images > 100:
        print()
        print("  ✓ Enough data to start training!")
        print("  Next step: Run prepare_dataset.py to organize the data")
    elif total_images > 0:
        print()
        print("  ⚠ Limited data. Training will work but accuracy may be lower.")
        print("  Consider downloading more datasets manually.")
    else:
        print()
        print("  ✗ No images downloaded. Please check errors above.")
        print("  You may need to accept dataset terms on Kaggle website first.")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
