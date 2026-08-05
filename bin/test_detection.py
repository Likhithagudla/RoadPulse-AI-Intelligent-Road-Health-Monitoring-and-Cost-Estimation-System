
import sys
import os
sys.path.append(r'd:\Road_AI_Project\ai_models\scripts')
from detection_service import RoadDefectDetector

def test():
    detector = RoadDefectDetector(conf=0.05) # Super low threshold for testing
    images = [
        r'd:\Road_AI_Project\uploads\images\1fdf302e.jpg',
        r'd:\Road_AI_Project\uploads\images\3e584dfa.jpg',
        r'd:\Road_AI_Project\uploads\images\4a353040.jpg'
    ]
    
    for img_path in images:
        print(f"\n--- Testing {os.path.basename(img_path)} ---")
        if not os.path.exists(img_path):
            print(f"File not found: {img_path}")
            continue
            
        result = detector.detect_image(img_path)
        detections = result.get('detections', [])
        print(f"Total detections: {len(detections)}")
        
        for d in detections:
            print(f"  - {d['class_name']} ({d['severity']}): {d['confidence']:.2f}")

if __name__ == "__main__":
    test()
