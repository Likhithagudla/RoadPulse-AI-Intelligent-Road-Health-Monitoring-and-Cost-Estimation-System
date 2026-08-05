
import sys
import os
sys.path.append(r'd:\Road_AI_Project\ai_models\scripts')
from detection_service import RoadDefectDetector

def test_manhole():
    detector = RoadDefectDetector(conf=0.01) # Use ensemble
    img_path = r'd:\Road_AI_Project\ai_models\dataset\unified\images\test\Manholes_000069.jpg'
    
    print(f"\n--- Testing Manhole Detection: {os.path.basename(img_path)} ---")
    if not os.path.exists(img_path):
        print(f"File not found: {img_path}")
        return
        
    result = detector.detect_image(img_path)
    detections = result.get('detections', [])
    print(f"Total detections: {len(detections)}")
    
    for d in detections:
        print(f"  - {d['class_name']} (ID: {d['class_id']}): {d['confidence']:.2f}")

if __name__ == "__main__":
    test_manhole()
