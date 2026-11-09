"""
RoadPulse AI - Multi-mode Model Pipeline CLI Wrapper
Provides unified train/validate/export/test modes delegating to ai_models.modules.
"""

import sys
import argparse
from pathlib import Path

# Add ai_models root to python path
AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.trainer import ModelTrainer
from modules.evaluator import ModelEvaluator
from modules.detector import RoadDefectDetector
from modules.config_loader import ensure_dataset_yaml_path, DEFAULT_WEIGHTS, EXPORT_DIR


def main():
    parser = argparse.ArgumentParser(description="RoadPulse AI Model Pipeline")
    parser.add_argument("--mode", type=str, default="train", choices=["train", "validate", "export", "test", "full"])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args()

    ensure_dataset_yaml_path()

    if args.mode in ("train", "full"):
        print("[INFO] Initiating training...")
        trainer = ModelTrainer(epochs=args.epochs, batch_size=args.batch)
        trainer.train()

    if args.mode in ("validate", "full"):
        print("[INFO] Evaluating on independent test split...")
        evaluator = ModelEvaluator()
        report = evaluator.evaluate(split="test")
        print(f"[METRICS] Test Box mAP@50: {report['overall_metrics']['box']['mAP50']}")

    if args.mode in ("export", "full"):
        print("[INFO] Exporting model to ONNX...")
        from ultralytics import YOLO
        model = YOLO(str(DEFAULT_WEIGHTS))
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        onnx_file = model.export(format="onnx", dynamic=True)
        print(f"[EXPORT] Saved ONNX model to {onnx_file}")

    if args.mode in ("test", "full"):
        print("[INFO] Running detector smoke test...")
        detector = RoadDefectDetector()
        print(f"[DETECTOR] Initialized detector with classes: {detector.class_names}")


if __name__ == "__main__":
    main()
