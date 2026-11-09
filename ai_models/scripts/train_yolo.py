"""
RoadPulse AI - Model Training CLI Wrapper (Step 4)
Delegates to modularized ModelTrainer in ai_models.modules.trainer.
"""

import sys
from pathlib import Path

# Add ai_models root to python path
AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.trainer import ModelTrainer
from modules.config_loader import ensure_dataset_yaml_path


def main():
    print("=" * 60)
    print("  RoadPulse AI - YOLOv8 Model Training (Step 4)")
    print("=" * 60)

    yaml_path = ensure_dataset_yaml_path()
    print(f"[INFO] Using dataset configuration: {yaml_path}")

    trainer = ModelTrainer(
        base_model="yolov8n-seg.pt",
        imgsz=640,
        batch_size=4,
        epochs=30,
        lr0=0.001,
        patience=15,
        device=None,
    )

    metrics = trainer.train()
    print("\n[SUCCESS] Model training completed successfully.")
    return metrics


if __name__ == "__main__":
    main()
