"""
RoadPulse AI - Unified Dataset Preparation CLI
Ensures dataset directory structure, YAML references, and split mappings are aligned.
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
    print("  RoadPulse AI - Dataset Alignment & Verification")
    print("=" * 60)

    yaml_path = ensure_dataset_yaml_path()
    validator = DatasetValidator(DATASET_DIR)
    summary = validator.validate()

    print(f"[SUCCESS] Dataset mapped at: {yaml_path}")
    print(f"[INFO] Splits present: {list(summary['splits'].keys())}")
    print(f"[INFO] Total images: {summary['total_images']}")
    return summary


if __name__ == "__main__":
    main()
