import os
import requests
import zipfile
from roboflow import Roboflow
import kaggle

# --- CONFIGURATION ---
ROBOFLOW_API_KEY = "RPOBmjD1UhE2l7j05cCv"
SAVE_PATH = "D:/Road_AI_Project/ai_models/dataset"
os.makedirs(SAVE_PATH, exist_ok=True)

# 1. KAGGLE DATASETS (Terms must be accepted on website first)
KAGGLE_DATASETS = [
    "theol369/road-damage-dataset-potholes-cracks-and-manholes",
    "faridafzali/potholes-cracks-and-openmanholes-road-hazards",
    "programmerrdai/road-issues-detection-dataset",
    "sabidrahman/pothole-cracks-and-openmanhole",
    "lorenzoarcioni/road-damage-dataset-potholes-cracks-and-manholes",
    "andrewmvd/road-sign-detection",
    "thendu3/road-lane-marking-signs",
    "amerzish/road-defects-images",
    "ayushchauhan009/raveling-detection-ce784a-2023"
]

# 2. ROBOFLOW UNIVERSE DATASETS (Full Public Slugs: workspace/project/version)
ROBOFLOW_UNIVERSE = {
    "RDD2022": "rdd2022/rdd2022/1",
    "Federico_II": "university-federico-ii-ygjoa/road-damage-detection-i40w8/1",
    "Damage_Types": "suprava-priyadarshini/road-damage-types/1",
    "Storm_Drains": "asphalt-model/storm-drain-model-xetsc/1"
}

def download_roboflow():
    print("\n--- Downloading from ROBOFLOW Universe ---")
    try:
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        for name, path in ROBOFLOW_UNIVERSE.items():
            print(f"Fetching {name}...")
            try:
                # Direct project access using the path components
                parts = path.split("/")
                if len(parts) == 3:
                    workspace = parts[0]
                    project_id = parts[1]
                    version = int(parts[2])
                    
                    project = rf.workspace(workspace).project(project_id)
                    dataset = project.version(version).download("yolov8", location=os.path.join(SAVE_PATH, name))
                    print(f"DONE: {name}")
                else:
                    print(f"SKIP {name}: Invalid slug format {path}")
            except Exception as e:
                print(f"FAILED {name}: {e}")
    except Exception as e:
        print(f"ROBOFLOW CRITICAL ERROR: {e}")

def download_kaggle():
    print("\n--- Downloading from KAGGLE ---")
    print("----------------------------------------------------------------")
    print("IMPORTANT: If you see '403 Forbidden', you MUST visit the link")
    print("below and click 'Download' to accept the terms, then retry:")
    print("----------------------------------------------------------------")
    
    for dataset_slug in KAGGLE_DATASETS:
        target_dir = os.path.join(SAVE_PATH, dataset_slug.split("/")[-1])
        os.makedirs(target_dir, exist_ok=True)
        try:
            print(f"Downloading {dataset_slug}...")
            kaggle.api.dataset_download_files(dataset_slug, path=target_dir, unzip=True)
            print(f"DONE: {dataset_slug}")
        except Exception as e:
            if "403" in str(e):
                print(f"KAGGLE ERROR 403: Permission Denied for {dataset_slug}")
                print(f"ACTION REQUIRED: Go to https://www.kaggle.com/datasets/{dataset_slug}")
                print("Accept the terms on the website, then run this script again.")
            else:
                print(f"KAGGLE ERROR: {e}")

def check_mendeley():
    print("\n--- Checking MENDELEY (Rutting) ---")
    target_dir = os.path.join(SAVE_PATH, "Mendeley_Rutting")
    if os.path.exists(target_dir) and len(os.listdir(target_dir)) > 0:
        print("[OK] Mendeley data found.")
    else:
        print("[MISSING] Mendeley Rutting data.")
        print("ACTION REQUIRED: Download manually from https://data.mendeley.com/datasets/hbv52stthk/1")
        print(f"and extract to: {target_dir}")

if __name__ == "__main__":
    print(f"Target Project Directory: {SAVE_PATH}")
    download_roboflow()
    download_kaggle()
    check_mendeley()
    print("\n========================================")
    print("PROCESS COMPLETE. Check logs for MISSING/FAILED items.")
    print("========================================")
