from pathlib import Path
import os
from ultralytics import YOLO
import yaml

ROOT = str(Path(__file__).resolve().parent.parent / "ai_models")
WEIGHTS = os.path.join(ROOT, "weights", "best.pt")
TEST_IMAGES = os.path.join(ROOT, "dataset/unified/test/images")
CONFIG = os.path.join(ROOT, "config.yaml")

def check_model_performance():
    if not os.path.exists(WEIGHTS):
        print("Model not found")
        return

    model = YOLO(WEIGHTS)
    
    # Get class names
    with open(CONFIG, 'r') as f:
        conf = yaml.safe_load(f)
    names = conf.get('names', {})
    
    print(f"Testing on images in {TEST_IMAGES}...")
    if not os.path.exists(TEST_IMAGES):
        print("No test images found")
        return

    images = [f for f in os.listdir(TEST_IMAGES) if f.endswith(('.jpg', '.png'))]
    if not images:
        print("No images found in test dir")
        return

    results = model.predict(source=TEST_IMAGES, conf=0.01, imgsz=640, verbose=False)
    
    overall_counts = {}
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = names.get(cls_id, f"Unknown_{cls_id}")
            overall_counts[cls_name] = overall_counts.get(cls_name, 0) + 1
            
    print("\nOverall Detections (across all test images at 0.01 conf):")
    for cls, count in sorted(overall_counts.items(), key=lambda x: -x[1]):
        print(f"  {cls}: {count}")

if __name__ == "__main__":
    check_model_performance()
