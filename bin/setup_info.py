import os

# Define the root path relative to the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_models"))

# 1. DEFECTS (The targets we need to detect)
CLASSES = [
    "Pothole", 
    "Edge Deterioration", 
    "Alligator Cracking", 
    "Rutting", 
    "Subsidence", 
    "Cracking", 
    "Bleeding", 
    "Fretting", 
    "Repaired Pothole", 
    "Line Marking",
    "Storm Drain", 
    "Manhole", 
    "Guard Rail", 
    "Traffic Sign"
]

# 2. DATASET SOURCES
SOURCES = {
    "Kaggle": "https://www.kaggle.com/datasets/road-damage-detection",
    "Roboflow": "https://universe.roboflow.com/search?q=pavement+distress",
    "Mendeley": "https://data.mendeley.com/datasets/hbv52stthk/1" # For Rutting
}

def check_setup():
    print("--- Road AI Project Structure ---")
    for folder in ["dataset", "weights", "scripts"]:
        path = os.path.join(ROOT_DIR, folder)
        if os.path.exists(path):
            print(f"[OK] Found: {path}")
        else:
            print(f"[MISSING] {path}")

if __name__ == "__main__":
    check_setup()
    print("\nNext step: Download 'kaggle.json' to start fetching data.")
