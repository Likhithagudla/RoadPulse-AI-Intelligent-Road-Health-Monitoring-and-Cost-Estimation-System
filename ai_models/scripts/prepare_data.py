"""
RoadPulse AI - Dataset Preparation & Integrity Verification CLI (Step 3)
Verifies annotation integrity, split distribution, and class consistency.
"""

import sys
from pathlib import Path

# Add ai_models root to python path
AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.dataset_validator import DatasetValidator
from modules.config_loader import ensure_dataset_yaml_path, DATASET_DIR


def main():
    print("=" * 60)
    print("  RoadPulse AI - Dataset Integrity & Validator (Step 3)")
    print("=" * 60)

    yaml_path = ensure_dataset_yaml_path()
    print(f"[INFO] Verified dataset configuration: {yaml_path}")
    print(f"[INFO] Unified dataset location: {DATASET_DIR}")

    validator = DatasetValidator(DATASET_DIR)
    report = validator.validate()

    print(f"[REPORT] Total Images: {report['total_images']}")
    print(f"[REPORT] Total Instances: {report['total_instances']}")
    print(f"[REPORT] Detected Classes: {dict(report['detected_classes'])}")
    print(f"[REPORT] Data Leakage: {'None' if not report['data_leakage_detected'] else 'DETECTED'}")
    print(f"[STATUS] Dataset Valid: {report['is_valid']}")

    return report


if __name__ == "__main__":
    main()
