"""
RoadPulse AI - Step 5: Test Model CLI Wrapper
Executes defect detection across test images and outputs calibrated damage assessments.
"""

import sys
from pathlib import Path

# Add ai_models root to python path
AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.detector import RoadDefectDetector
from modules.config_loader import DEFAULT_WEIGHTS, DATASET_DIR


def main():
    print("=" * 60)
    print("  RoadPulse AI - Model Testing (Step 5)")
    print("=" * 60)

    test_dir = DATASET_DIR / "images" / "test"
    test_images = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))

    if not test_images:
        print(f"[WARN] No test images found in {test_dir}")
        return

    print(f"[INFO] Initializing detector with: {DEFAULT_WEIGHTS}")
    detector = RoadDefectDetector(weights_path=DEFAULT_WEIGHTS, conf_threshold=0.15)

    sample = test_images[0]
    print(f"[INFO] Testing inference on sample image: {sample.name}")
    result = detector.detect_image(sample, region="Default")

    print(f"[RESULT] Success: {result['success']}")
    print(f"[RESULT] Total Detections: {result.get('total_detections', 0)}")
    for i, det in enumerate(result.get("detections", []), start=1):
        print(f"  [{i}] {det['class_name']} ({det['confidence']:.2f}) - Severity: {det['severity']} - Cost: INR {det['detailed_cost_breakdown']['estimated_cost_inr']:.2f}")


if __name__ == "__main__":
    main()
